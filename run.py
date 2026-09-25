from app import create_app, db

app = create_app()

if __name__ == '__main__':
    # This creates all 8 tables in PostgreSQL if they don't already exist.
    # Safe to run every time - it won't touch tables that already exist.
    with app.app_context():
        db.create_all()
        print("Database tables created successfully.")

    app.run(debug=True)
