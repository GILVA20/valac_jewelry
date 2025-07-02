from flask import flash, redirect, request, url_for
from flask_login import current_user
from flask_admin import BaseView, expose
import logging
from flask import request, redirect, url_for, flash, current_app
from flask_admin import Admin, BaseView, expose
from flask_login import current_user
import logging
from .admin_bulk_upload import BulkUploadAdminView
from collections import Counter
import json

class SupabaseProductAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))

    @expose('/', methods=['GET'])
    def index(self):
        supabase = self.admin.app.supabase
        response = supabase.table("products").select("*").execute()
        if not response.data:
            logging.error("Error al obtener productos: %s", response)
            products = []
        else:
            products = response.data
            logging.info("Productos obtenidos: %d", len(products))
        return self.render('admin/supabase_products.html', products=products)
    @expose('/update-stock/<int:product_id>', methods=['POST'])
    def update_stock(self,product_id):
            supabase = current_app.supabase
            try:
                # Validar existencia del campo
                if 'stock_total' not in request.form:
                    flash("Falta el valor de stock_total en el formulario", "error")
                    return redirect(url_for('supabase_products.index'))

                new_stock = request.form.get('stock_total').strip()

                # Validación robusta
                if not new_stock.isdigit() or int(new_stock) < 0:
                    flash("El valor de stock debe ser un número entero positivo", "error")
                    return redirect(url_for('supabase_products.index'))

                new_stock_int = int(new_stock)

                # Intentar actualizar en Supabase
                response = supabase.table("products") \
                                .update({"stock_total": new_stock_int}) \
                                .eq("id", product_id) \
                                .execute()

                if response.error:
                    current_app.logger.error(f"[update_stock] Error Supabase: {response.error}")
                    flash("Ocurrió un error al actualizar el stock. Revisa los logs.", "error")
                else:
                    flash("Stock actualizado correctamente", "success")

            except Exception as e:
                current_app.logger.exception("[update_stock] Excepción inesperada")
                flash("Error inesperado al actualizar el stock", "error")

            return redirect(url_for('supabase_products.index'))

    @expose('/apply_discount', methods=['POST'])
    def apply_discount(self):
        supabase = self.admin.app.supabase
        ids = request.form.getlist('product_ids')
        pct = int(request.form.get('bulk_descuento_pct', 0))

        for pid in ids:
            # Obtener precio original
            resp = supabase.table("products").select("precio").eq("id", int(pid)).execute()
            if resp.data:
                precio = float(resp.data[0]['precio'])
                precio_desc = round(precio * (1 - pct/100), 2)
                # Actualizar descuento_pct y precio_descuento
                supabase.table("products").update({
                    "descuento_pct": pct,
                    "precio_descuento": precio_desc
                }).eq("id", int(pid)).execute()

        flash(f"Descuento {pct}% aplicado a {len(ids)} producto(s).", "success")
        return redirect(url_for('.index'))

    @expose('/remove_discount', methods=['POST'])
    def remove_discount(self):
        supabase = self.admin.app.supabase
        ids = request.form.getlist('product_ids')

        for pid in ids:
            supabase.table("products").update({
                "descuento_pct": 0,
                "precio_descuento": 0
            }).eq("id", int(pid)).execute()

        flash(f"Descuentos eliminados de {len(ids)} producto(s).", "info")
        return redirect(url_for('.index'))

    @expose('/new', methods=['GET', 'POST'])
    def new(self):
        if request.method == 'POST':
            nombre         = request.form.get('nombre')
            descripcion    = request.form.get('descripcion')
            precio         = request.form.get('precio')
            descuento_pct  = int(request.form.get('descuento_pct', 0))
            tipo_producto  = request.form.get('tipo_producto')
            genero         = request.form.get('genero')
            tipo_oro       = request.form.get('tipo_oro')
            imagen_url     = request.form.get('imagen')
            imagenes_raw   = request.form.get('imagenes_multiples', "[]")  # JSON string

            if not all([nombre, descripcion, precio, tipo_producto, genero, tipo_oro, imagen_url]):
                flash("Todos los campos son obligatorios.", "error")
                return self.render('admin/supabase_new_product.html', config=current_app.config)

            precio = float(precio)
            precio_descuento = round(precio * (1 - descuento_pct/100), 2)

            supabase = self.admin.app.supabase
            data = {
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": precio,
                "descuento_pct": descuento_pct,
                "precio_descuento": precio_descuento,
                "tipo_producto": tipo_producto,
                "genero": genero,
                "tipo_oro": tipo_oro,
                "imagen": imagen_url  # Primera imagen como principal
            }

            response = supabase.table("products").insert(data).execute()

            if not response.data:
                flash("Error al agregar el producto: " + str(response), "error")
                return redirect(url_for('.index'))

            nuevo_producto = response.data[0]
            producto_id = nuevo_producto["id"]

            # Procesar imágenes múltiples si están disponibles
            imagenes = []
            try:
                if imagenes_raw:
                    imagenes = json.loads(imagenes_raw)
                    if not isinstance(imagenes, list):
                        imagenes = []
            except Exception as e:
                imagenes = []
                current_app.logger.warning("Error al parsear imagenes_multiples: %s", str(e))

            for i, url in enumerate(imagenes):
                try:
                    insert_resp = supabase.table("product_images").insert({
                        "product_id": producto_id,
                        "imagen": url,
                        "orden": i
                    }).execute()
                    if insert_resp.error:
                        current_app.logger.error("Error insertando imagen %s para producto %s: %s", url, producto_id, insert_resp.error)
                except Exception as ex:
                    current_app.logger.exception("Excepción insertando imagen múltiple: %s", str(ex))

            flash("Producto agregado exitosamente con imágenes.", "success")
            return redirect(url_for('.index'))

        return self.render('admin/supabase_new_product.html', config=current_app.config)

    @expose('/delete/<int:product_id>', methods=['POST'])
    def delete_product(self, product_id):
        supabase = self.admin.app.supabase
        response = supabase.table("products").delete().eq("id", product_id).execute()
        if not response.data:
            flash("Error al eliminar el producto.", "error")
        else:
            flash("Producto eliminado exitosamente.", "success")
        return redirect(url_for('.index'))

    @expose('/edit/<int:id>', methods=['GET', 'POST'])
    def edit_product(self, id):
        supabase = self.admin.app.supabase

        if request.method == 'POST':
            nombre    = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            precio    = float(request.form.get('precio'))
            descuento_pct = int(request.form.get('descuento_pct', 0))
            precio_descuento = round(precio * (1 - descuento_pct/100), 2)
            tipo_producto = request.form.get('tipo_producto')
            genero    = request.form.get('genero')
            tipo_oro  = request.form.get('tipo_oro')
            imagen_url = request.form.get('imagen')

            response = supabase.table("products").update({
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": precio,
                "descuento_pct": descuento_pct,
                "precio_descuento": precio_descuento,
                "tipo_producto": tipo_producto,
                "genero": genero,
                "tipo_oro": tipo_oro,
                "imagen": imagen_url
            }).eq("id", id).execute()

            if not response.data:
                flash("Error al actualizar el producto.", "error")
            else:
                flash("Producto actualizado exitosamente.", "success")
            return redirect(url_for('.index'))

        # GET: traer datos actuales, incluyendo descuento
        resp = supabase.table("products").select("*").eq("id", id).execute()
        if not resp.data:
            flash("Producto no encontrado.", "error")
            return redirect(url_for('.index'))
        product = resp.data[0]

        images_response = supabase.table("product_images") \
            .select("*").eq("product_id", id).order("orden").execute()
        gallery = images_response.data or []

        return self.render(
            'admin/supabase_edit_product.html',
            product=product,
            gallery=gallery,
            config=current_app.config
        )

    @expose('/delete_gallery_image/<int:image_id>', methods=['POST'])
    def delete_gallery_image(self, image_id):
        supabase = self.admin.app.supabase
        response = supabase.table("product_images").delete().eq("id", image_id).execute()
        if not response.data:
            flash("Error al eliminar la imagen de la galería.", "error")
        else:
            flash("Imagen eliminada exitosamente.", "success")
        return redirect(url_for('.edit_product', id=request.form.get('product_id')))

    @expose('/gallery')
    def gallery(self):
        supabase = self.admin.app.supabase
        response = supabase.table("products").select("id, nombre, imagen").execute()
        media_items = response.data or []
        return self.render('admin/supabase_gallery.html', media_items=media_items)

# Nueva vista para Ventas
class SalesAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    
    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))
    
    @expose('/')
    def index(self):
        # Aquí iría la lógica para listar ventas
        # Por ejemplo, consultar la base de datos de ventas
        sales = []  # Simulación de datos de ventas
        logging.info("Ventas obtenidas: %s", sales)
        return self.render('admin/sales.html', sales=sales)

# Nueva vista para Pagos/Cobranza
class PaymentsAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    
    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))
    
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        if request.method == 'POST':
            # Procesar el registro de un nuevo pago (obtención y validación de datos del formulario)
            # Por ejemplo: monto, fecha, método de pago, etc.
            flash("Pago registrado exitosamente.", "success")
            return redirect(url_for('.index'))
        payments = []  # Simulación de datos de pagos
        logging.info("Pagos obtenidos: %s", payments)
        return self.render('admin/payments.html', payments=payments)

# Nueva vista para Reportes
class ReportsAdmin(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    
    def inaccessible_callback(self, name, **kwargs):
        flash("Debes iniciar sesión como administrador para acceder a esta sección.", "error")
        return redirect(url_for('auth.login', next=request.url))
    
    @expose('/')
    def index(self):
        # Generar reportes; por ejemplo, total de ventas, pagos, productos, etc.
        report_data = {
            "total_sales": 100,
            "total_payments": 50,
            "inventory_count": 200
        }
        logging.info("Reportes generados: %s", report_data)
        return self.render('admin/reports.html', report_data=report_data)
