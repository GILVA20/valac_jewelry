"""
VALAC Studio – AI-powered jewelry photography blueprint.

Endpoints
---------
GET  /admin/studio/               → Serve React SPA
POST /admin/studio/generate/stage1 → Start async Stage 1 job → returns job_id
POST /admin/studio/generate/stage2 → Start async Stage 2 job → returns job_id
GET  /admin/studio/job/<job_id>    → Poll job status/result
GET  /admin/studio/products        → Active products list
POST /admin/studio/save            → Upload image to Supabase Storage
"""

import os
import json
import base64
import time
import uuid
import logging
import threading

from flask import Blueprint, current_app, request, jsonify, send_file
from flask_login import login_required

logger = logging.getLogger(__name__)

studio_bp = Blueprint("studio", __name__, url_prefix="/admin/studio")

# ── In-memory job store (single-dyno safe) ───────────────────────────
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


# ── Lazy SDK clients ─────────────────────────────────────────────────


def _claude():
    """Return a cached Anthropic client."""
    if not hasattr(current_app, "_claude_client"):
        import anthropic

        current_app._claude_client = anthropic.Anthropic(
            api_key=current_app.config["ANTHROPIC_API_KEY"],
        )
    return current_app._claude_client


def _gemini():
    """Return a cached Google GenAI client."""
    if not hasattr(current_app, "_gemini_client"):
        from google import genai

        current_app._gemini_client = genai.Client(
            api_key=current_app.config["GOOGLE_GENAI_API_KEY"],
        )
    return current_app._gemini_client


# ── Helpers ──────────────────────────────────────────────────────────


def _claude_model():
    return current_app.config.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")


def _parse_claude_json(msg) -> dict:
    """Parse a Claude response message into a JSON dict, handling common issues."""
    if msg.stop_reason != "end_turn":
        current_app.logger.warning(
            "Claude response truncated (stop_reason=%s)", msg.stop_reason
        )
    raw = msg.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Claude often puts literal newlines inside JSON string values;
        # collapse them to spaces so the JSON is valid.
        raw_fixed = raw.replace("\r\n", " ").replace("\n", " ")
        return json.loads(raw_fixed)


def _ask_claude_json(system_prompt: str, image_b64: str, media_type: str = "image/jpeg") -> dict:
    """Send an image + system prompt to Claude, expect JSON back."""
    msg = _claude().messages.create(
        model=_claude_model(),
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                    {"type": "text", "text": system_prompt},
                ],
            }
        ],
    )
    return _parse_claude_json(msg)


def _ask_claude_json_multi(system_prompt: str, images: list[tuple[str, str]]) -> dict:
    """Send multiple images + system prompt to Claude, expect JSON back.
    images: list of (base64_data, mime_type) tuples.
    """
    content = []
    for img_b64, mime in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": img_b64,
            },
        })
    content.append({"type": "text", "text": system_prompt})
    msg = _claude().messages.create(
        model=_claude_model(),
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )
    return _parse_claude_json(msg)


def _gemini_generate_image(prompt: str) -> str:
    """Call Imagen 4 (text-to-image). Returns base64 PNG."""
    from google.genai import types

    model_name = current_app.config.get(
        "GEMINI_IMAGEN_MODEL", "imagen-4.0-fast-generate-001"
    )
    response = _gemini().models.generate_images(
        model=model_name,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/png",
        ),
    )
    if response.generated_images:
        return base64.b64encode(
            response.generated_images[0].image.image_bytes
        ).decode()
    raise RuntimeError("Imagen did not return any images")


def _detect_mime(b64_data: str) -> str:
    """Detect image MIME type from the first bytes of base64-encoded data."""
    header = base64.b64decode(b64_data[:32])
    if header[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if header[:2] == b'\xff\xd8':
        return "image/jpeg"
    if header[:4] == b'RIFF' and header[8:12] == b'WEBP':
        return "image/webp"
    # HEIC/HEIF: ftyp box with heic/heix/mif1 brand
    if header[4:8] == b'ftyp':
        brand = header[8:12]
        if brand in (b'heic', b'heix', b'mif1', b'hevc'):
            return "image/heic"
    return "image/jpeg"  # safe default


def _gemini_edit_image(prompt: str, images_b64: list) -> str:
    """Call Gemini Flash (vision + generation) with images. Returns base64 PNG."""
    from google.genai import types

    parts = []
    for img_b64 in images_b64:
        parts.append(
            types.Part.from_bytes(
                data=base64.b64decode(img_b64),
                mime_type=_detect_mime(img_b64),
            )
        )
    parts.append(types.Part.from_text(text=prompt))

    model_name = current_app.config.get(
        "GEMINI_FLASH_MODEL", "gemini-2.5-flash-image"
    )
    response = _gemini().models.generate_content(
        model=model_name,
        contents=parts,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"],
            temperature=0.4,
        ),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            return base64.b64encode(part.inline_data.data).decode()
    raise RuntimeError("Gemini Flash did not return an image")


def _validate_with_claude(image_b64: str, validation_prompt: str) -> dict:
    """Send a generated image to Claude for QC validation."""
    return _ask_claude_json(validation_prompt, image_b64, _detect_mime(image_b64))


# ── Stage 1 internals ───────────────────────────────────────────────


STAGE1_ANALYSIS_PROMPT = """\
You are a professional jewelry photography director and product describer \
for AI image generation. Your output will be fed DIRECTLY to an image \
generation model (Gemini). The model has NO common sense — it cannot infer \
what it cannot see described.

Analyze this raw jewelry photo with extreme precision. Describe the EXACT \
morphology of the object, not the category.

RULES:
- NEVER use vague words: "distinctive", "elegant", "beautiful", "unique" \
  — describe SHAPE not QUALITY.
- Estimate dimensions in mm.
- Describe textures as a materials photographer would: \
  "diagonal groove pattern creating V-shaped light reflections".
- For multi-metal pieces: specify exactly which zones are yellow / white / rose gold.
- If there are multiple pieces (e.g. pair of earrings), describe the count \
  and arrangement.

Return ONLY valid JSON with these fields:
{
  "metal": string — exact alloy, color temperature, and finish per zone \
(e.g. "14k warm yellow gold, high mirror polish on flat faces, \
brushed satin on edges"),
  "tipo": string — technical jewelry type \
(e.g. "hoop earring", "figaro chain bracelet", "solitaire pendant"),
  "tamaño": "small and delicate" | "medium" | "statement",
  "silhouette": string — exact geometric shape name, proportions, \
cross-section profile, and dimensions in mm. \
(e.g. "elongated capsule/pill shape, 28mm tall × 10mm wide × 3mm thick, \
flat beveled edges, rounded end-caps"),
  "surface_texture": string — finish type per zone with pattern geometry \
(e.g. "body: 6 raised longitudinal facets with mirror polish creating \
prismatic light catch. Edges: micro-brushed satin. Inner surface: smooth \
mirror polish"),
  "structural_details": string — closure mechanism, hinges, connectors, \
moving parts, construction method \
(e.g. "snap-hinge closure at top with cylindrical barrel connector, \
single-piece stamped construction"),
  "decorative_elements": string or null — stones (shape, size, color, \
setting type, position), enamel (color, shape, coverage), applied motifs \
(hearts/crosses/text with exact position), mixed metals per zone \
(e.g. "3 calado heart motifs on front face: left=yellow gold, \
center=white gold, right=rose gold, each 4mm wide" or null),
  "piece_count": string — how many pieces visible and their spatial \
relationship (e.g. "pair of 2 identical earrings shown side by side, \
faces forward, 5mm apart"),
  "descripcion_completa": string — A STRUCTURED description (minimum 80 words) \
in English written for an image generation model. Must include ALL of the \
following in labeled sections:\n\
SILHOUETTE: [exact shape, dimensions, cross-section]\n\
SURFACE: [finish types per zone, texture patterns, reflectivity]\n\
STRUCTURE: [closure, connectors, construction]\n\
DECORATIONS: [stones/enamel/motifs with positions]\n\
ARRANGEMENT: [piece count, orientation, which details face camera]\n\
METAL: [alloy, color temperature, which zones are which finish]\n\
This description must be precise enough that someone who has NEVER seen \
this piece can recreate it exactly from text alone.
}

CRITICAL:
- Return ONLY valid JSON, no markdown, no extra text.
- Every field must describe what you SEE, not what category it belongs to.
- If you cannot determine a detail, estimate it and note "(estimated)".
"""


def _stage1_gemini_prompt(desc: str, tamaño: str) -> str:
    return (
        "You are a professional jewelry product photographer and photo retoucher. "
        "Generate a hyper-realistic, editorial-quality product photograph.\n\n"
        "CRITICAL INSTRUCTION: Reproduce the EXACT piece described below. "
        "Do NOT invent new shapes, do NOT simplify geometry, do NOT change proportions. "
        "Every detail in the description MUST appear in the generated image.\n"
        "\nJEWELRY PIECE (reproduce EXACTLY):\n"
        f"{desc}\n"
        "\nBACKGROUND & SETTING:\n"
        "- Pure white background (#FFFFFF), perfectly clean, no gradients\n"
        "- Soft diffused studio lighting from upper left at 45 degrees\n"
        "- One subtle fill light from the right to open shadows slightly\n"
        "- Piece centered in frame with generous breathing room\n"
        "- Natural soft contact shadow directly below the piece\n"
        "\nPHOTOGRAPHY SPECS:\n"
        "- Medium telephoto macro lens, f/8 for maximum depth of field\n"
        "- The entire jewelry piece must be tack sharp from clasp to clasp\n"
        "- No hands, no props, no fabric, no surface texture — floating product style\n"
        "\nMETAL & MATERIAL QUALITY:\n"
        "- Specular highlights must follow the light source consistently\n"
        "- Show realistic polish marks, micro-scratches, casting lines — "
        "NOT perfect CGI surface\n"
        "- Inter-reflections between links/components if applicable\n"
        "- Stones must show their internal optical properties (brilliance, fire)\n"
        "\nCRITICAL SCALE RULE:\n"
        f"This is a {tamaño} piece. "
        "It must occupy NO MORE than 35% of the frame. "
        "Preserve exact real-world proportions. Do not enlarge or exaggerate.\n"
        "\nOUTPUT REQUIREMENTS:\n"
        "- Square 1:1 format\n"
        "- Maximum resolution and detail\n"
        "- Photorealistic — indistinguishable from a $3,000 professional studio shoot\n"
        "- A jeweler must be able to assess construction quality from this photo\n"
        "\nDO NOT:\n"
        "- Do not add sparkle overlays, lens flares, or AI glow effects\n"
        "- Do not smooth metal to look like a render\n"
        "- Do not add any text, watermarks, or background objects"
    )


def _stage1_validation_prompt(desc: str) -> str:
    return (
        "You are a quality control director for a luxury jewelry e-commerce company. "
        "You are reviewing a generated product photo.\n\n"
        f"The jewelry piece should be: {desc}\n\n"
        "Evaluate these criteria strictly:\n"
        "1. SHARPNESS: Is the jewelry piece clearly visible and tack-sharp?\n"
        "2. ACCURACY: Does it match the description? (metal type, color, structure)\n"
        "3. BACKGROUND: Is the background clean pure white?\n"
        "4. SCALE: Are the proportions realistic — not oversized or exaggerated?\n"
        "5. REALISM: Does metal look photographed (micro-scratches, polish marks) "
        "or does it look like a CGI render?\n\n"
        "Return JSON only:\n"
        '{\n'
        '  "status": "approved" | "review",\n'
        '  "reason": string (one sentence summary),\n'
        '  "corrections": string | null — If status is \"review\", write a SPECIFIC, '
        'actionable correction instruction that can be appended to the generation prompt '
        'to fix the issue. Examples: "Scale the piece down by 30%%, it is too large", '
        '"The metal color should be warm yellow gold, not white silver", '
        '"Add more specular highlights, the surface looks too matte". '
        'If status is \"approved\", set to null.\n'
        '}'
    )


def _process_stage1_single(img_b64: str, feedback: str = "") -> dict:
    """Stage 1: Claude analyzes the raw photo → Gemini generates product shot."""
    # 1 ─ Claude analyses the raw photo
    analysis = _ask_claude_json(STAGE1_ANALYSIS_PROMPT, img_b64)
    desc = analysis.get("descripcion_completa", "")
    tamaño = analysis.get("tamaño", "medium")

    # 2 ─ Gemini generates a clean product photo from the original
    product_prompt = _stage1_gemini_prompt(desc, tamaño)
    if feedback:
        product_prompt += (
            "\n\nUSER CORRECTION — APPLY THESE FIXES:\n"
            + feedback
        )
    try:
        product_b64 = _gemini_edit_image(product_prompt, [img_b64])
        product_status = "approved"
    except Exception:
        logger.exception("Stage 1 product generation failed, using original")
        product_b64 = img_b64
        product_status = "review"

    return {
        "image_base64": img_b64,               # original photo
        "product_image_base64": product_b64,    # generated product photo
        "status": product_status,
        "reason": "Foto analizada y producto generado",
        "description": desc,
    }


# ── Stage 2 internals ───────────────────────────────────────────────


_STAGE2_CLAUDE_SYSTEM = """\
You are an expert luxury jewelry photographer and AI prompt engineer.

I am giving you TWO images:
- Image 1: A product photo of the jewelry piece (studio shot).
- Image 2: A base lifestyle photo of a model — the target for compositing.

YOUR TASK: Analyze BOTH images carefully, then write a direct, \
commanding Gemini image-generation prompt that composites the jewelry \
onto the model. The prompt you write will be sent to Gemini along with \
both images (Image 1 = base photo, Image 2 = product photo).

Return ONLY valid JSON (no markdown fences):
{
  "tamaño": "small and delicate" | "medium" | "statement",
  "body_placement": string,
  "prompt": string (at least 300 words, direct and commanding)
}

CRITICAL — The "prompt" you write MUST follow this EXACT style \
(direct commands, real measurements, explicit prohibitions):

─── STRUCTURE YOUR PROMPT LIKE THIS ───

PARAGRAPH 1 — SCENE PRESERVATION:
"Generate a photorealistic close-up of [body part] of a [man/woman] \
[wearing/showing] [exact jewelry description], based on Image 1. \
The base image is [describe what you see in Image 2 — framing, clothing, \
skin tone, hair, background]. Keep the framing, camera angle, lighting, \
skin texture, [hair/beard], and clothing IDENTICAL."

PARAGRAPH 2 — PRODUCT PRESERVATION RULE:
"PRODUCT PRESERVATION RULE: \
The jewelry from Image 2 must remain EXACTLY as shown. \
Do not redesign [specific part]. Do not modify [specific part]. \
Do not simplify details. Do not change the metal color. \
Do not invent new shapes. The [piece] must be identical to Image 2."

PARAGRAPH 3 — REALISTIC SCALE (use REAL mm measurements):
From your analysis of Image 1, estimate and specify:
- Chain/band thickness in mm (e.g. "4-5mm chain")
- Pendant/charm size in cm (e.g. "2.5-3cm tall")
- Overall piece dimensions relative to body (e.g. "about the size of a thumbnail")
- Explicit warning: "Do NOT create an oversized statement piece"

PARAGRAPH 4 — LENGTH, POSITION & DRAPE:
- Where exactly the piece sits on the body
- How far from anatomical landmarks (e.g. "4-6cm below collarbone")
- How gravity affects the drape
- Whether it should look tight or relaxed

PARAGRAPH 5 — PHYSICAL REALISM:
- Chain/metal must follow body contours naturally
- Contact shadows where metal touches skin
- Metal reflections must match the scene lighting from Image 1
- Pendant/charm hangs vertically due to gravity

PARAGRAPH 6 — PHOTOGRAPHY STYLE:
"Ultra-realistic luxury jewelry photography. \
High-end [men's/women's] jewelry advertising style. \
85mm lens look. Soft studio lighting. \
Sharp [gold/silver] highlights. Natural skin texture."

PARAGRAPH 7 — FINAL RESULT:
"A hyperrealistic image of a [man/woman] wearing the EXACT jewelry \
from Image 2. The jewelry must appear physically worn on the [body part], \
with realistic proportions, correct [chain length/ring fit/earring hang], \
and exact [pendant/charm/stone] size matching Image 2."

─── KEY RULES FOR YOUR PROMPT ───

1. Be SPECIFIC about the jewelry from Image 1 — describe exactly what you see: \
   metal type, finish, chain style, pendant shape, stones, textures.
2. Use REAL measurements in mm/cm estimated from the product photo.
3. Include at least 5 explicit "Do NOT" rules about preserving the product design.
4. Reference Image 1 and Image 2 by name in the prompt.
5. Describe what you actually see in the base photo (Image 2): \
   skin tone, clothing, hair, lighting direction, background.
6. The output image must look like the person is WEARING the real jewelry, \
   photographed with a professional camera — NOT a CGI render.
"""


def _stage2_build_prompt(prod_b64: str, base_b64: str, sexo: str, desc: str) -> tuple:
    """Ask Claude to analyze product + base photos and build a hyper-detailed Gemini prompt."""
    system_with_context = (
        _STAGE2_CLAUDE_SYSTEM
        + f"\n\nPiece description (from Stage 1 analysis): {desc}\n"
        + f"Model sex in base photo: {sexo}\n"
        + "Image 1 is the product photo. Image 2 is the base lifestyle photo.\n"
        + "Analyze BOTH images and return the JSON."
    )

    analysis = _ask_claude_json_multi(
        system_with_context,
        [
            (prod_b64, _detect_mime(prod_b64)),
            (base_b64, _detect_mime(base_b64)),
        ],
    )

    tamaño = analysis.get("tamaño", "medium")
    mounting_prompt = analysis.get("prompt", "")

    # Fallback: should never trigger with a well-behaved Claude response
    if not mounting_prompt:
        mounting_prompt = (
            f"You are a professional jewelry photographer. "
            f"Keep Image 1 (base lifestyle photo) EXACTLY as is. "
            f"Naturally composite the {desc} from Image 2 onto the model "
            f"at the anatomically correct position for a {sexo} model. "
            f"The piece is {tamaño} — place at real-world scale. "
            "Match all lighting, shadows, and reflections to the base photo. "
            "The result must look like a real photograph, not a composite."
        )

    return mounting_prompt, tamaño


def _stage2_validation_prompt(desc: str) -> str:
    return (
        "You are a quality control director reviewing a lifestyle jewelry composite.\n\n"
        f"The jewelry should be: {desc}\n\n"
        "Evaluate these criteria strictly:\n"
        "1. PLACEMENT: Is the jewelry naturally placed on the correct body part?\n"
        "2. SCALE: Are proportions correct relative to the human body? "
        "Is it too big, too small, or just right?\n"
        "3. LIGHTING: Do the jewelry reflections and shadows match the scene lighting?\n"
        "4. INTEGRATION: Does it look photographed or pasted/composited?\n"
        "5. BASE PRESERVATION: Is the original base photo untouched "
        "(no skin smoothing, no background changes)?\n\n"
        "Return JSON only:\n"
        '{\n'
        '  "status": "approved" | "review",\n'
        '  "reason": string (one sentence summary),\n'
        '  "corrections": string | null — If status is \"review\", write a SPECIFIC, '
        'actionable correction instruction for the image generator. '
        'Be precise with percentages, positions, and directions. Examples: '
        '"The bracelet is 20%% too large, scale it down to match a real bracelet on this wrist size", '
        '"Move the necklace pendant 1cm lower, it should sit at the sternum not the collarbone", '
        '"The earring shadow falls to the right but the scene light comes from the left — flip shadow direction", '
        '"Metal color is too warm/yellow, this is silver .925, make it cooler white". '
        'If status is \"approved\", set to null.\n'
        '}'
    )


def _process_stage2_single(prod_b64: str, base_b64: str, sexo: str, desc: str, feedback: str = "") -> dict:
    """Process one product image through Stage 2 compositing."""
    # 1 ─ Claude builds mounting prompt
    mounting_prompt, _tamaño = _stage2_build_prompt(prod_b64, base_b64, sexo, desc)
    if feedback:
        mounting_prompt += (
            "\n\nUSER CORRECTION — APPLY THESE FIXES:\n"
            + feedback
        )

    # 2 ─ Gemini composites (base + product images)
    generated_b64 = _gemini_edit_image(mounting_prompt, [base_b64, prod_b64])

    # 3 ─ Claude validates
    val_prompt = _stage2_validation_prompt(desc)
    validation = _validate_with_claude(generated_b64, val_prompt)
    status = validation.get("status", "review")
    reason = validation.get("reason", "")
    corrections = validation.get("corrections", "")

    # 4 ─ Retry once with corrective feedback if 'review'
    if status == "review" and corrections:
        try:
            corrected_prompt = (
                mounting_prompt
                + "\n\nCORRECTION FROM QUALITY REVIEW — APPLY THESE FIXES:\n"
                + corrections
            )
            retry_b64 = _gemini_edit_image(corrected_prompt, [base_b64, prod_b64])
            retry_val = _validate_with_claude(retry_b64, val_prompt)
            return {
                "image_base64": retry_b64,
                "status": retry_val.get("status", "review"),
                "reason": retry_val.get("reason", reason),
            }
        except Exception:
            logger.exception("Stage 2 retry failed")

    return {
        "image_base64": generated_b64,
        "status": status,
        "reason": reason,
    }


# ── Async job helpers ────────────────────────────────────────────────


def _create_job() -> str:
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"status": "processing", "result": None}
    return job_id


def _complete_job(job_id: str, result: dict):
    with _jobs_lock:
        _jobs[job_id] = {"status": "done", "result": result}


def _fail_job(job_id: str, error: str):
    with _jobs_lock:
        _jobs[job_id] = {"status": "error", "result": {"error": error}}


def _run_in_thread(app, job_id: str, fn, *args, **kwargs):
    """Run fn inside Flask app context and complete/fail the job."""
    def _worker():
        with app.app_context():
            try:
                result = fn(*args, **kwargs)
                _complete_job(job_id, result)
            except Exception as e:
                logger.exception("Job %s failed", job_id)
                _fail_job(job_id, str(e))
    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# ── Routes ───────────────────────────────────────────────────────────


@studio_bp.route("/")
@login_required
def index():
    """Serve the React SPA (built by Vite into static/studio/)."""
    index_path = os.path.join(current_app.static_folder, "studio", "index.html")
    if not os.path.isfile(index_path):
        return (
            "VALAC Studio no está disponible. "
            "Ejecuta 'npm run build' en valacstudio/ primero."
        ), 404
    return send_file(index_path)


@studio_bp.route("/job/<job_id>")
@login_required
def poll_job(job_id):
    """Poll an async job status."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] == "processing":
        return jsonify({"status": "processing"})
    # Clean up completed job
    with _jobs_lock:
        _jobs.pop(job_id, None)
    return jsonify({"status": job["status"], **job["result"]})


@studio_bp.route("/generate/stage1", methods=["POST"])
@login_required
def generate_stage1():
    """Stage 1: raw photo → Claude analysis → Gemini product photo → Claude QC."""
    data = request.get_json(force=True)
    images = data.get("images", [])
    feedbacks = data.get("feedback", [])

    if not images:
        return jsonify({"error": "No images provided"}), 400

    job_id = _create_job()
    app = current_app._get_current_object()

    def _do_stage1():
        results = []
        for idx, img_b64 in enumerate(images):
            fb = feedbacks[idx] if idx < len(feedbacks) else ""
            try:
                result = _process_stage1_single(img_b64, feedback=fb)
                results.append(result)
            except Exception as e:
                logger.exception("Stage 1 error for one image")
                results.append({
                    "image_base64": "",
                    "status": "review",
                    "reason": f"Error processing image: {e}",
                    "description": "",
                })
        return {"results": results}

    _run_in_thread(app, job_id, _do_stage1)
    return jsonify({"job_id": job_id})


@studio_bp.route("/generate/stage2", methods=["POST"])
@login_required
def generate_stage2():
    """Stage 2: product + base image → Gemini compositing → Claude QC."""
    data = request.get_json(force=True)
    product_images = data.get("product_images", [])
    base_image_key = data.get("base_image", "")
    sexo = data.get("sexo", "")
    descriptions = data.get("descriptions", [])
    feedbacks = data.get("feedback", [])

    if not product_images or not base_image_key:
        return jsonify({"error": "Missing product images or base image key"}), 400

    # Load base image from static folder — try both .jpg and .png
    bases_dir = os.path.join(current_app.static_folder, "studio", "bases")
    base_path = None
    for ext in (".jpg", ".png", ".jpeg", ".webp"):
        candidate = os.path.join(bases_dir, f"{base_image_key}{ext}")
        if os.path.isfile(candidate):
            base_path = candidate
            break
    if base_path is None:
        return jsonify({"error": f"Base image not found: {base_image_key}"}), 404

    with open(base_path, "rb") as f:
        base_b64 = base64.b64encode(f.read()).decode()

    job_id = _create_job()
    app = current_app._get_current_object()

    def _do_stage2():
        results = []
        for i, prod_b64 in enumerate(product_images):
            desc = descriptions[i] if i < len(descriptions) else ""
            fb = feedbacks[i] if i < len(feedbacks) else ""
            try:
                result = _process_stage2_single(prod_b64, base_b64, sexo, desc, feedback=fb)
                results.append(result)
            except Exception as e:
                logger.exception("Stage 2 error for one image")
                results.append({
                    "image_base64": "",
                    "status": "review",
                    "reason": f"Error compositing: {e}",
                })
        return {"results": results}

    _run_in_thread(app, job_id, _do_stage2)
    return jsonify({"job_id": job_id})


@studio_bp.route("/products")
@login_required
def get_products():
    """Return active products for the save-to-catalog dropdown."""
    data = (
        current_app.supabase.table("products")
        .select("id, nombre")
        .order("nombre")
        .execute()
    )
    return jsonify({"products": data.data or []})


@studio_bp.route("/save", methods=["POST"])
@login_required
def save_image():
    """Upload a generated image to Supabase Storage; return the public URL."""
    data = request.get_json(force=True)
    image_b64 = data.get("image_base64", "")

    if not image_b64:
        return jsonify({"error": "No image provided"}), 400

    # Decode
    image_bytes = base64.b64decode(image_b64)

    # Convert to WebP (Pillow is already installed)
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes))
    webp_buffer = io.BytesIO()
    img.save(webp_buffer, format="WEBP", quality=90)
    image_bytes = webp_buffer.getvalue()

    # Build filename: studio-generated/{timestamp}_{producto_id}.webp
    timestamp = int(time.time())
    producto_id = data.get("producto_id", "unknown")
    safe_id = "".join(c for c in str(producto_id) if c.isalnum() or c in "_-")
    filename = f"studio-generated/{timestamp}_{safe_id}.webp"

    current_app.supabase.storage.from_("CatalogoJoyasValacJoyas").upload(
        filename, image_bytes, {"content-type": "image/webp"}
    )

    cdn_base = current_app.config.get("CDN_BASE_URL", "")
    image_url = f"{cdn_base}{filename}"

    return jsonify({"success": True, "image_url": image_url})
