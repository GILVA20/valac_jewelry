from flask import request, redirect, url_for, flash, current_app
from flask_admin import BaseView, expose
import logging

class SupabaseProductAdmin(BaseView):
    @expose('/')
    def index(self):
        supabase = self.admin.app.supabase
        response = supabase.table("products").select("*").execute()
        if not response.data:
            logging.error("Error al obtener productos: " + str(response))
            products = []
        else:
            products = response.data
            logging.info(f"Productos obtenidos: {products}")
        return self.render('admin/supabase_products.html', products=products)
    
    @expose('/new', methods=['GET', 'POST'])
    def new(self):
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            precio = request.form.get('precio')
            tipo_producto = request.form.get('tipo_producto')
            genero = request.form.get('genero')
            tipo_oro = request.form.get('tipo_oro')
            imagen_url = request.form.get('imagen')
            
            if not all([nombre, descripcion, precio, tipo_producto, genero, tipo_oro, imagen_url]):
                flash("Todos los campos son obligatorios.", "error")
                return self.render('admin/supabase_new_product.html', config=current_app.config)
            
            supabase = self.admin.app.supabase
            data = {
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": float(precio),
                "tipo_producto": tipo_producto,
                "genero": genero,
                "tipo_oro": tipo_oro,
                "imagen": imagen_url
            }
            response = supabase.table("products").insert(data).execute()
            if not response.data:
                flash("Error al agregar el producto: " + str(response), "error")
            else:
                flash("Producto agregado exitosamente.", "success")
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
            nombre = request.form.get('nombre')
            descripcion = request.form.get('descripcion')
            precio = request.form.get('precio')
            tipo_producto = request.form.get('tipo_producto')
            genero = request.form.get('genero')
            tipo_oro = request.form.get('tipo_oro')
            imagen_url = request.form.get('imagen')
            response = supabase.table("products").update({
                "nombre": nombre,
                "descripcion": descripcion,
                "precio": float(precio),
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

        response = supabase.table("products").select("*").eq("id", id).execute()
        if not response.data:
            flash("Producto no encontrado.", "error")
            return redirect(url_for('.index'))
        product = response.data[0]
        images_response = supabase.table("product_images").select("*").eq("product_id", id).order("orden").execute()
        gallery = images_response.data if images_response.data else []
        return self.render('admin/supabase_edit_product.html', product=product, gallery=gallery, config=current_app.config)

    @expose('/delete_gallery_image/<int:image_id>', methods=['POST'])
    def delete_gallery_image(self, image_id):
        supabase = self.admin.app.supabase
        response = supabase.table("product_images").delete().eq("id", image_id).execute()
        if not response.data:
            flash("Error al eliminar la imagen de la galería.", "error")
        else:
            flash("Imagen eliminada exitosamente.", "success")
        return redirect(url_for('.edit_product', id=request.form.get('product_id')))

    # Agrega el endpoint "gallery"
    @expose('/gallery')
    def gallery(self):
        supabase = self.admin.app.supabase
        response = supabase.table("products").select("id, nombre, imagen").execute()
        media_items = response.data if response.data else []
        return self.render('admin/supabase_gallery.html', media_items=media_items)
