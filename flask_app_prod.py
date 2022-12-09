from api import create_app

flask_app = create_app(config_name="prod")

if __name__ == "__main__":
    flask_app.run(debug=True, port=5003, host='0.0.0.0')
