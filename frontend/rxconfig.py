import reflex as rx

config = rx.Config(
    app_name="amarktai_dashboard",
    backend_port=8000,
    frontend_port=3000,
    db_url="postgresql://amarktai:amarktai_secure_pass@localhost:5433/amarktai_mkt",
)
