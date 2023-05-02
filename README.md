# Connectly python bot

## Instructions

### Online
You can access the deployed version by visiting this [link](https://orca-app-sx77z.ondigitalocean.app/)
And chet with the [bot](https://t.me/ConnectlyTestBot)

### Local development
- Create te Docker image by running `docker build -t connectly-test .` on your terminal (you can change `connectly-test` for what ever name you prefer)
- Then run `docker run -d -p 8000:8000 --name cont1 connectly-test`

Now you can access the fronend on [http://localhost:8000/](http://localhost:8000/) and use the bot [link](https://t.me/ConnectlyTestBot).

 **Note** Since we are using sqlite3 as a local db, everytime you lauch a container the db will be deleted and restarted from scratch
**NOTE** This method will interfere with the one live on "production" so if you want to try it with out issues you can try with your own API key