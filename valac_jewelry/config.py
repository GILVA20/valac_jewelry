# valac_jewelry/config.py
class Config:
    SECRET_KEY = 'tu-clave-secreta-aqui'  # Cambia este valor por una clave segura
    # Puedes agregar otras configuraciones si lo deseas:
    # DEBUG = True
    # Configuraciones de Supabase:
    SUPABASE_URL = 'https://fqxiyrvhwadydqlnswzb.supabase.co'
    SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZxeGl5cnZod2FkeWRxbG5zd3piIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzg2MjQ0OTQsImV4cCI6MjA1NDIwMDQ5NH0.2PgtsDbmBBrCHbP7UnMpClTnX2VJavbeF-hipLHH90g'
    SUPABASE_STORAGE_URL = 'https://fqxiyrvhwadydqlnswzb.supabase.co/storage/v1/object/public/CatalogoJoyasValacJoyas/products/'