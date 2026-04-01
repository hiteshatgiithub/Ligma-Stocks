# LIGMA Stocks

## This README explains how to run the given website using flask from command-line.

Make sure you have all the required libraries installed given in the requirements.txt file.

Steps:
1. Open the terminal and go to the directory containing the app.py file.
2. For Windows (Anaconda terminal), run the following command: set API_KEY="apikey"

   For Linux, run: export API_KEY=apikey

   Where apikey = pk_4aba43ae608a423ea9cefaac7ab4279f

   If this apikey does not work, go to https://iexcloud.io/console/tokens, create a new account and use a new api key generated there.
3. Now run the command: flask run
4. Open the localhost site generated in the terminal. The link might look something like this: http://127.0.0.1:5000

And it's done! You can buy, sell and monitor your stocks with ease.
