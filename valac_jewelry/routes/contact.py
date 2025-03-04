from flask import Blueprint, render_template, request, redirect, flash, url_for

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/contact', methods=['GET'])
def contact():
    return render_template('contact.html')

@contact_bp.route('/contact/send', methods=['POST'])
def send():
    # Extract data from the contact form
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')
    
    # Here you can process the data (validate, send email, store in database, etc.)
    flash("Tu mensaje ha sido enviado. ¡Gracias por contactarnos!", "success")
    
    # Redirect back to the contact page (or another page if preferred)
    return redirect(url_for('contact.contact'))
