from flask import Blueprint, request, jsonify
import pandas as pd
import io
from ..new_product import create_or_update_product

bulk_upload_bp = Blueprint('bulk_upload_bp', __name__)

@bulk_upload_bp.route("/bulk-upload", methods=["POST"])
def bulk_upload():
    if "csv" not in request.files:
        return jsonify({"error": "CSV no proporcionado"}), 400

    csv_file = request.files["csv"]
    image_paths = request.form.get("image_paths", "")
    image_paths_list = [p.strip() for p in image_paths.split(",") if p.strip()]

    try:
        content = csv_file.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(content))
    except Exception as e:
        return jsonify({"error": "❌ Error: CSV no válido", "detail": str(e)}), 400

    required_columns = ["nombre", "descripcion", "precio", "tipo_producto", "genero", "tipo_oro", "imagen"]
    if not all(col in df.columns for col in required_columns):
        return jsonify({"error": "❌ Error: CSV no válido - columnas faltantes"}), 400

    total = len(df)
    report = {"success": [], "warnings": [], "errors": []}
    if total > 50:
        df = df.head(50)
        report["warnings"].append(f"⚠️ Solo se procesaron 50 de {total} productos.")

    for _, row in df.iterrows():
        try:
            result = create_or_update_product(row, image_paths_list=image_paths_list)
            if result.get("estado") == "success":
                report["success"].append(result.get("mensaje"))
            elif result.get("estado") == "warning":
                report["warnings"].append(result.get("mensaje"))
        except Exception as e:
            nombre = row.get("nombre", "Producto sin nombre")
            report["errors"].append(f"❌ {nombre}: {str(e)}")
    
    return jsonify(report)
