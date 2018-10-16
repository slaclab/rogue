# Installing Rogue and Anaconda behind a proxy

To install rogue and anaconda behind a firewall you will need an ssl capable https proxy. I have used mitmproxy with success:

````
$ mitmproxy --list-host=gateway.machine.com --list-port=8080
````

You will execute a number of steps to enable proxy for wget, git and anaconda

````
$ setenv https_proxy gateway.machine.com:8080
$ git config --global https.proxy https://gateway.machine.com:8080
$ git config --global http.sslVerify false
````

Create a file $HOME/.condarc and add the following lines:

````
proxy_servers:
   http:http://gateway.machine.com:8080
   https:https://gateway.machine.com:8080

ssl_verify: false
````

