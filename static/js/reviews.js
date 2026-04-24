/**
 * reviews.js — VALAC Joyas Reviews Module
 * Handles: loading, rendering, form submission, lightbox, voting
 * Uses: jQuery (global), FontAwesome (global)
 */
(function () {
  "use strict";

  const API = "/api/reviews/";
  const API_STATS = "/api/reviews/stats";

  let currentPage = 1;
  let currentStars = null;
  let currentMedia = false;
  let hasMore = false;
  let mode = "home";        // home | page | product
  let productId = null;
  let productName = "";

  // Lightbox state
  let lbMedia = [];
  let lbIndex = 0;

  /* ──────────────────────────────────────────
     INIT
  ────────────────────────────────────────── */
  function init() {
    const section = document.getElementById("reviews-section");
    if (!section) return;

    // Prevent jQuery from caching AJAX GET responses (fixes stale data on mobile refresh)
    $.ajaxSetup({ cache: false });

    mode = section.dataset.mode || "home";
    productId = section.dataset.productId || null;
    productName = section.dataset.productName || "";

    // Pre-fill product name in form
    if (productName) {
      const inp = document.getElementById("review-producto");
      if (inp) inp.value = productName;
    }
    if (productId) {
      const inp = document.getElementById("review-product-id");
      if (inp) inp.value = productId;
    }

    // Show filters only in page mode
    if (mode === "page") {
      const filters = document.getElementById("reviews-filters");
      if (filters) filters.classList.remove("hidden");
    }

    setupStarPicker();
    setupMediaUpload();
    setupFormSubmit();
    setupFilters();
    setupCharCounter();
    setupKeyboard();

    loadStats(function () {
      loadReviews(true);
    });
  }

  /* ──────────────────────────────────────────
     LOAD STATS
  ────────────────────────────────────────── */
  function loadStats(callback) {
    let url = API_STATS;
    if (productId) url += "?product_id=" + productId;

    $.getJSON(url, function (data) {
      if (!data || data.total === 0) return;

      var summary = document.getElementById("reviews-summary");
      if (summary) summary.classList.remove("hidden");

      // Stars display
      var full = Math.floor(data.promedio);
      var half = data.promedio - full >= 0.5;
      var starsHtml = "★".repeat(full);
      if (half) starsHtml += "★";
      starsHtml += "☆".repeat(5 - full - (half ? 1 : 0));

      if (mode === "home") {
        // Compact summary for home carousel
        $("#reviews-summary-compact").removeClass("hidden");
        $("#reviews-avg-compact").text(data.promedio);
        $("#reviews-avg-stars-compact").text(starsHtml);
        $("#reviews-total-compact").text(data.total + (data.total === 1 ? " reseña" : " reseñas"));
      } else {
        // Full summary with distribution for page/product
        $("#reviews-summary-full").removeClass("hidden");
        $("#reviews-avg").text(data.promedio);
        $("#reviews-total").text(data.total + (data.total === 1 ? " reseña" : " reseñas"));
        $("#reviews-avg-stars").text(starsHtml);

        // Distribution bars
        var dist = data.distribucion;
        var distHtml = "";
        for (var s = 5; s >= 1; s--) {
          var count = dist[String(s)] || 0;
          var pct = data.total > 0 ? (count / data.total * 100) : 0;
          distHtml += '<div class="dist-row">' +
            '<span class="text-gray-600 w-4">' + s + '</span>' +
            '<span class="text-[#D5A300]">★</span>' +
            '<div class="dist-bar"><div class="dist-fill" style="width:' + pct + '%"></div></div>' +
            '<span class="text-gray-400 w-8 text-right">' + count + '</span>' +
            '</div>';
        }
        $("#reviews-distribution").html(distHtml);
      }
    }).always(function () {
      if (callback) callback();
    });
  }

  /* ──────────────────────────────────────────
     LOAD REVIEWS
  ────────────────────────────────────────── */
  function loadReviews(reset) {
    if (reset) {
      currentPage = 1;
      $("#reviews-grid").empty();
    }

    let params = { page: currentPage, per_page: 9 };
    if (productId) params.product_id = productId;
    if (currentStars) params.estrellas = currentStars;
    if (currentMedia) params.con_media = "1";
    if (mode === "home") params.featured = "1";

    $.getJSON(API, params, function (data) {
      const grid = document.getElementById("reviews-grid");
      const reviews = data.reviews || [];
      hasMore = data.has_more;

      if (reviews.length === 0 && currentPage === 1) {
        $("#reviews-empty").removeClass("hidden");
        $("#reviews-grid").addClass("hidden");
        $("#reviews-load-more").addClass("hidden");
        $("#reviews-see-all").addClass("hidden");
        return;
      }

      $("#reviews-empty").addClass("hidden");
      $("#reviews-grid").removeClass("hidden");

      reviews.forEach(function (r) {
        $(grid).append(renderCard(r));
      });

      // Load more / see all
      if (mode === "home") {
        $("#reviews-load-more").addClass("hidden");
        $("#reviews-see-all").removeClass("hidden");
        initHomeCarousel();
      } else {
        $("#reviews-see-all").addClass("hidden");
        if (hasMore) {
          $("#reviews-load-more").removeClass("hidden");
        } else {
          $("#reviews-load-more").addClass("hidden");
        }
      }

      // AOS re-init for new cards
      if (typeof AOS !== "undefined") AOS.refresh();
    });
  }

  function loadMore() {
    currentPage++;
    loadReviews(false);
  }

  /* ──────────────────────────────────────────
     HOME CAROUSEL (Slick)
  ────────────────────────────────────────── */
  function initHomeCarousel() {
    var $grid = $("#reviews-grid");
    if ($grid.hasClass("slick-initialized")) return;

    var count = $grid.children().length;
    if (count === 0) return;

    // Remove grid classes for Slick
    $grid.removeClass("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5");

    // Adapt to the actual number of reviews to prevent Slick from breaking
    var show = Math.min(count, 3);

    $grid.slick({
      slidesToShow: show,
      slidesToScroll: 1,
      autoplay: count > 1,
      autoplaySpeed: 4000,
      arrows: count > show,
      dots: count > show,
      pauseOnHover: true,
      infinite: count > show,
      prevArrow: '<button type="button" class="slick-prev" aria-label="Anterior"><i class="fas fa-chevron-left"></i></button>',
      nextArrow: '<button type="button" class="slick-next" aria-label="Siguiente"><i class="fas fa-chevron-right"></i></button>',
      responsive: [
        { breakpoint: 1024, settings: { slidesToShow: Math.min(count, 2) } },
        { breakpoint: 640, settings: { slidesToShow: 1 } }
      ]
    });
  }

  /* ──────────────────────────────────────────
     RENDER CARD
  ────────────────────────────────────────── */
  function renderCard(r) {
    const stars = "★".repeat(r.estrellas) + "☆".repeat(5 - r.estrellas);
    const voted = localStorage.getItem("rv_" + r.id);
    const voteClass = voted ? " voted" : "";

    let mediaHtml = "";
    if (r.media_urls && r.media_urls.length > 0) {
      mediaHtml = '<div class="review-media-grid">';
      r.media_urls.forEach(function (url, idx) {
        const isVideo = /\.(mp4|mov)$/i.test(url);
        const clickAttr = 'onclick="window.ValacReviews.openLightbox(' + JSON.stringify(r.media_urls) + ',' + idx + ')"';
        if (isVideo) {
          mediaHtml += '<div class="review-video-thumb" ' + clickAttr + '><i class="fas fa-play"></i></div>';
        } else {
          mediaHtml += '<img src="' + escHtml(url) + '" class="review-media-thumb" ' + clickAttr + ' alt="Foto de reseña" loading="lazy">';
        }
      });
      mediaHtml += '</div>';
    }

    return '<div class="review-card" data-aos="fade-up">' +
      '<div class="flex items-center justify-between mb-2">' +
        '<div>' +
          '<span class="font-semibold text-gray-800">' + escHtml(r.nombre) + '</span>' +
          (r.verificado ? ' <span class="verified-badge"><i class="fas fa-check-circle"></i> Verificado</span>' : '') +
        '</div>' +
        '<span class="text-xs text-gray-400">' + escHtml(r.fecha_relativa) + '</span>' +
      '</div>' +
      '<div class="review-stars text-sm mb-1">' + stars + '</div>' +
      '<p class="text-xs text-gray-400 mb-2">' + escHtml(r.producto) + '</p>' +
      '<p class="text-gray-700 text-sm leading-relaxed">' + escHtml(r.texto) + '</p>' +
      mediaHtml +
      '<div class="mt-3 flex items-center gap-3">' +
        '<button class="review-util-btn' + voteClass + '" ' + (voted ? 'disabled' : 'onclick="window.ValacReviews.voteUtil(' + r.id + ', this)"') + '>' +
          '<i class="far fa-thumbs-up"></i> Útil <span class="util-count">' + (r.util_count || 0) + '</span>' +
        '</button>' +
      '</div>' +
    '</div>';
  }

  function escHtml(s) {
    if (!s) return "";
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  /* ──────────────────────────────────────────
     FILTERS
  ────────────────────────────────────────── */
  function setupFilters() {
    $(document).on("click", ".reviews-filter-btn", function () {
      var btn = $(this);
      if (btn.data("media")) {
        // Toggle media filter
        currentMedia = !currentMedia;
        btn.toggleClass("active", currentMedia);
      } else {
        // Stars filter
        $(".reviews-filter-btn[data-stars]").removeClass("active");
        btn.addClass("active");
        var val = btn.data("stars");
        currentStars = val === "all" ? null : parseInt(val);
      }
      loadReviews(true);
    });
  }

  /* ──────────────────────────────────────────
     STAR PICKER
  ────────────────────────────────────────── */
  function setupStarPicker() {
    $(document).on("click", ".star-pick", function () {
      var val = parseInt($(this).data("star"));
      $("#estrellas-input").val(val);
      $(".star-pick").each(function () {
        $(this).toggleClass("active", parseInt($(this).data("star")) <= val);
      });
    });
  }

  /* ──────────────────────────────────────────
     MEDIA UPLOAD
  ────────────────────────────────────────── */
  function setupMediaUpload() {
    var dropzone = document.getElementById("media-dropzone");
    var input = document.getElementById("media-input");
    if (!dropzone || !input) return;

    dropzone.addEventListener("click", function () { input.click(); });

    // Drag & drop
    dropzone.addEventListener("dragover", function (e) {
      e.preventDefault();
      dropzone.classList.add("border-[#D5A300]");
    });
    dropzone.addEventListener("dragleave", function () {
      dropzone.classList.remove("border-[#D5A300]");
    });
    dropzone.addEventListener("drop", function (e) {
      e.preventDefault();
      dropzone.classList.remove("border-[#D5A300]");
      if (e.dataTransfer.files.length) {
        input.files = e.dataTransfer.files;
        renderPreviews(input.files);
      }
    });

    input.addEventListener("change", function () {
      renderPreviews(this.files);
    });
  }

  function renderPreviews(files) {
    var container = document.getElementById("media-preview");
    if (!container) return;
    container.innerHTML = "";
    var max = Math.min(files.length, 6);
    for (var i = 0; i < max; i++) {
      var f = files[i];
      var div = document.createElement("div");
      div.className = "relative w-16 h-16 rounded-lg overflow-hidden border";
      if (f.type.startsWith("video/")) {
        div.innerHTML = '<div class="w-full h-full bg-gray-800 flex items-center justify-center"><i class="fas fa-play text-white"></i></div>';
      } else {
        var img = document.createElement("img");
        img.className = "w-full h-full object-cover";
        img.src = URL.createObjectURL(f);
        div.appendChild(img);
      }
      container.appendChild(div);
    }
    if (files.length > 6) {
      container.insertAdjacentHTML("beforeend", '<p class="text-xs text-red-500 w-full">Máximo 6 archivos. Se enviarán solo los primeros 6.</p>');
    }
  }

  /* ──────────────────────────────────────────
     CHAR COUNTER
  ────────────────────────────────────────── */
  function setupCharCounter() {
    $(document).on("input", "#review-texto", function () {
      var len = this.value.length;
      var label = document.getElementById("char-count");
      if (label) {
        if (len < 50) {
          label.textContent = "(" + len + "/50 mín.)";
          label.className = "text-red-400 font-normal";
        } else {
          label.textContent = "(" + len + " caracteres ✓)";
          label.className = "text-green-500 font-normal";
        }
      }
    });
  }

  /* ──────────────────────────────────────────
     FORM SUBMIT
  ────────────────────────────────────────── */
  function setupFormSubmit() {
    $(document).on("submit", "#review-form", function (e) {
      e.preventDefault();
      var form = this;
      var errDiv = document.getElementById("review-error");
      var submitBtn = document.getElementById("review-submit");
      errDiv.classList.add("hidden");

      // Client-side validations
      var estrellas = parseInt($("#estrellas-input").val());
      if (!estrellas || estrellas < 1) {
        showFormError("Selecciona una calificación de estrellas.");
        return;
      }
      var texto = form.texto.value.trim();
      if (texto.length < 50) {
        showFormError("Tu reseña debe tener al menos 50 caracteres (tienes " + texto.length + ").");
        return;
      }

      var fd = new FormData(form);

      // Add media files from the input
      var mediaInput = document.getElementById("media-input");
      if (mediaInput && mediaInput.files.length > 0) {
        // Clear existing 'media' entries and re-add from file input
        fd.delete("media");
        var max = Math.min(mediaInput.files.length, 6);
        for (var i = 0; i < max; i++) {
          fd.append("media", mediaInput.files[i]);
        }
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Enviando...";

      $.ajax({
        url: API,
        method: "POST",
        data: fd,
        processData: false,
        contentType: false,
        success: function () {
          document.getElementById("review-form").classList.add("hidden");
          document.getElementById("review-success").classList.remove("hidden");
        },
        error: function (xhr) {
          var msg = "Error al enviar. Intenta de nuevo.";
          try { msg = JSON.parse(xhr.responseText).error || msg; } catch (e) {}
          showFormError(msg);
        },
        complete: function () {
          submitBtn.disabled = false;
          submitBtn.textContent = "Enviar Reseña";
        }
      });
    });
  }

  function showFormError(msg) {
    var errDiv = document.getElementById("review-error");
    if (errDiv) {
      errDiv.textContent = msg;
      errDiv.classList.remove("hidden");
    }
  }

  /* ──────────────────────────────────────────
     MODAL OPEN / CLOSE
  ────────────────────────────────────────── */
  function openForm() {
    var modal = document.getElementById("review-modal");
    if (modal) {
      modal.classList.remove("hidden");
      document.body.style.overflow = "hidden";
      // Reset form state
      var form = document.getElementById("review-form");
      var success = document.getElementById("review-success");
      if (form) { form.reset(); form.classList.remove("hidden"); }
      if (success) success.classList.add("hidden");
      $(".star-pick").removeClass("active");
      $("#estrellas-input").val("0");
      document.getElementById("review-error").classList.add("hidden");
      var preview = document.getElementById("media-preview");
      if (preview) preview.innerHTML = "";
      // Re-fill product name if set
      if (productName) {
        var inp = document.getElementById("review-producto");
        if (inp) inp.value = productName;
      }
      if (productId) {
        var pidInp = document.getElementById("review-product-id");
        if (pidInp) pidInp.value = productId;
      }
    }
  }

  function closeForm() {
    var modal = document.getElementById("review-modal");
    if (modal) {
      modal.classList.add("hidden");
      document.body.style.overflow = "";
    }
  }

  /* ──────────────────────────────────────────
     LIGHTBOX
  ────────────────────────────────────────── */
  function openLightbox(mediaUrls, index) {
    lbMedia = mediaUrls;
    lbIndex = index || 0;
    renderLightbox();
    document.getElementById("review-lightbox").classList.remove("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeLightbox(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById("review-lightbox").classList.add("hidden");
    document.body.style.overflow = "";
    // Pause video if playing
    var vid = document.querySelector("#lb-content video");
    if (vid) vid.pause();
  }

  function lbNav(dir) {
    lbIndex = (lbIndex + dir + lbMedia.length) % lbMedia.length;
    renderLightbox();
  }

  function renderLightbox() {
    var container = document.getElementById("lb-content");
    var url = lbMedia[lbIndex];
    var isVideo = /\.(mp4|mov)$/i.test(url);

    if (isVideo) {
      container.innerHTML = '<video src="' + escHtml(url) + '" controls autoplay class="rounded-lg" style="max-width:100%;max-height:85vh"></video>';
    } else {
      container.innerHTML = '<img src="' + escHtml(url) + '" alt="Reseña" class="rounded-lg" style="max-width:100%;max-height:85vh">';
    }

    // Nav buttons visibility
    document.getElementById("lb-prev").style.display = lbMedia.length > 1 ? "" : "none";
    document.getElementById("lb-next").style.display = lbMedia.length > 1 ? "" : "none";
  }

  /* ──────────────────────────────────────────
     VOTE UTIL
  ────────────────────────────────────────── */
  function voteUtil(reviewId, btn) {
    if (localStorage.getItem("rv_" + reviewId)) return;

    $.post(API + reviewId + "/util", function (data) {
      localStorage.setItem("rv_" + reviewId, "1");
      $(btn).addClass("voted").prop("disabled", true);
      $(btn).find(".util-count").text(data.util_count);
    });
  }

  /* ──────────────────────────────────────────
     KEYBOARD
  ────────────────────────────────────────── */
  function setupKeyboard() {
    document.addEventListener("keydown", function (e) {
      var lb = document.getElementById("review-lightbox");
      if (lb && !lb.classList.contains("hidden")) {
        if (e.key === "Escape") closeLightbox();
        if (e.key === "ArrowLeft") lbNav(-1);
        if (e.key === "ArrowRight") lbNav(1);
      }
      var modal = document.getElementById("review-modal");
      if (modal && !modal.classList.contains("hidden") && e.key === "Escape") {
        closeForm();
      }
    });
  }

  /* ──────────────────────────────────────────
     PUBLIC API
  ────────────────────────────────────────── */
  window.ValacReviews = {
    init: init,
    loadMore: loadMore,
    openForm: openForm,
    closeForm: closeForm,
    openLightbox: openLightbox,
    closeLightbox: closeLightbox,
    lbNav: lbNav,
    voteUtil: voteUtil
  };

  // Auto-init: covers first load + bfcache restoration (Safari iOS)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) {
      // Page restored from bfcache — re-init to load fresh data
      var $grid = $("#reviews-grid");
      if ($grid.hasClass("slick-initialized")) {
        $grid.slick("unslick");
        $grid.addClass("grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5");
      }
      init();
    }
  });
})();
