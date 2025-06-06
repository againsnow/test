from flask import Flask, request, redirect

app = Flask(__name__)
database = {}

def generate_id():
    from random import randint
    return str(randint(1000000, 9999999))

@app.route('/shorten', methods=['POST'])
def shorten():
    url = request.form['url']
    uid = generate_id()
    while uid in database:
        uid = generate_id()
    database[uid] = url
    return f"http://94.103.93.213:8000/{uid}"

@app.route('/<uid>')
def go(uid):
    url = database.get(uid)
    if url:
        return redirect(url)
    return "Ссылка не найдена", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)