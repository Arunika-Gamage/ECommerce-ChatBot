import nltk
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
import pickle
import numpy as np
import mysql.connector
from keras.models import load_model
import json
import random

nltk.download('words')
from nltk.corpus import words

#database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="RuniRoot123#",
    database="ecombot"
)

if db.is_connected():
    print("Connected to the database")

model = load_model('chatbot_model.h5')
intents = json.loads(open('intents.json').read())
word_s = pickle.load(open('words.pkl','rb'))
classes = pickle.load(open('classes.pkl','rb'))

def is_sentence_meaningless(sentence, word_s):
    s_set = set(sentence.lower().split())
    if s_set.difference(words.words()+word_s) == s_set:
        return True
    return False

def clean_up_sentence(sentence):
    # tokenize the pattern - split words into array
    sentence_words = nltk.word_tokenize(sentence)
    # stem each word - create short form for word
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

# return bag of words array: 0 or 1 for each word in the bag that exists in the sentence

def bow(sentence, word_s, show_details=True):
    # tokenize the pattern
    sentence_words = clean_up_sentence(sentence)
    # bag of words - matrix of N words, vocabulary matrix
    bag = [0]*len(word_s)  
    for s in sentence_words:
        for i,w in enumerate(word_s):
            if w == s: 
                # assign 1 if current word is in the vocabulary position
                bag[i] = 1
                if show_details:
                    print ("found in bag: %s" % w)
    return(np.array(bag))

def predict_class(sentence, model):

    # filter out predictions below a threshold
    p = bow(sentence, word_s,show_details=False)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
    # sort by strength of probability
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list

def getResponse(ints, intents_json):

    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']

    for i in list_of_intents:
        if(i['tag']== tag):
            result = random.choice(i['responses'])
            break
    return result

# Retrieving product information from the database

def handle_product_inquiry(product_name):
    cursor = db.cursor()
    try:
        cursor.execute("SELECT * FROM products WHERE name = %s", (product_name,))
        product = cursor.fetchone()

        if product:
            product_id, name, description, price, availability, promo_info  = product
            response = f"<br/><br/> Brand : {name}<br/> Description : {description}<br/> Price : ${price}<br/>"

            # Check for availability and promotions
            if availability:
                response += " Availability: In Stock<br/>"
            else:
                response += " Availability: Out of Stock<br/>"

            if promo_info:
                response += f" Promotions: {promo_info}<br/>"
            else:
                response += " No promotions for this laptop<br/>"

        else:
            response = "I couldn't find information about that product. Please try again."
    except Exception as e:
        response = f"An error occurred while retrieving the information: {str(e)}"
    finally:
        cursor.close()

    return response

# Get order details by order id

def get_order_by_id(order_id):

    cursor = db.cursor()
    query = "SELECT * FROM orders WHERE order_id = %s"

    # cursor.execute(query, (order_id,))
    cursor.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
    order_data = cursor.fetchone()

    # Fetch and print the results
    cursor.close()

    return order_data

# Tracking order

def order_tracking(order_refNo):

    cursor = db.cursor()
    query = " SELECT * FROM order_tracking WHERE order_refNo = %s "

    # cursor.execute(query, (order_id,))
    cursor.execute(query, (order_refNo,))
    # Fetch and print the results
    order_data = cursor.fetchone()
    cursor.close()  # Close the cursor and database connection
   
    return order_data


def chatbot_response(msg):
    
    res = ""  # Initialize the res variable with an empty string

    if is_sentence_meaningless(msg,word_s):
        ints = predict_class("INPUT_ERROR", model)
    else:
        ints = predict_class(msg, model)
    
    #ints = predict_class(msg, model)

    laptop_brands = ["lenovo", "asus","msi","acer","hp probook","apple macbook"]
    
    if any(keyword in msg.lower() for keyword in laptop_brands):
         # Check if any laptop brand keyword is found
        product_name = next(keyword for keyword in laptop_brands if keyword in msg.lower())

        res = "Allow me to provide you with the comprehensive laptop details you requested:<br/>"+ handle_product_inquiry(product_name)+ "<br/><br/>If you have any further questions, please feel free to ask."
        if not res:
            res = f"Sorry, we couldn't find information about {brand_name} laptops. Please try a different brand or ask another question."

    elif msg.startswith("get order by") or msg.startswith("my order id is ") or msg.startswith("id"):
        order_id = msg.split()[-1]

        order_data = get_order_by_id(order_id)
        if order_data:
            res = f"Order ID: {order_data[0]}<br/> , Product id: {order_data[1]}<br/> , Quantity: {order_data[2]}<br/> , Total price: {order_data[3]}<br/>, Order reference number: {order_data[4]}<br/> "
        else:
            res = "Your order is not in our database. Please check and re-enter."

    elif msg.startswith("LU") or msg.startswith("my reference no is LU0"):
         # Extract the order ID using regular expressions
        import re
        match = re.search(r'\bLU\d+\b', msg)
        if match:
            order_refNo = match.group()
            order_data = order_tracking(order_refNo)
            if order_data:
                res = f"{order_data[1]}"
            else:
                res = "Your order is not in our database. Please check and re-enter."
        else:
            res = "Invalid order reference number format. The reference number should start with 'LU' followed by 3 digits (e.g., LU123)."


    else:
        # If it's not a specific intent, use the previous code to get a response
        res = getResponse(ints, intents)

        # Check if a valid response was obtained
        if not res:
            res = "I'm sorry, I couldn't comprehend that. Could you please rephrase or ask a different question."
    
    return res


