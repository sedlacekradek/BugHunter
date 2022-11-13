from web import create_app

app = create_app()

## local ###
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
