from flask import Flask, render_template, request, jsonify
import json
from chatgui import chatbot_response


from flask_cors import CORS
intents = json.loads(open('intents.json').read())

app = Flask(__name__)
CORS(app)


@app.get("/")
def index_get():
    return render_template("base.html")


@app.post("/predict")
def predict():
    text = request.get_json().get("message")
    # TODO: check if text is valid
    res = chatbot_response(text)
    message = {"answer": res}
    return jsonify(message)




if __name__ == "__main__":
    app.run(debug=True)

