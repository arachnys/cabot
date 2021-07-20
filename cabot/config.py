import os


def config_charge():
    config = open("conf/development.env", "r")
    lines = config.read().splitlines()
    config.close()

    for line in lines:

        key = ''
        value = ''
        divider = 0
        
        if line != "":
            if line[0] != "#":

                divider = line.find('=')

                key = line[:divider]
                value = line[divider+1:]

                os.environ[key]=value
        else:
            pass




                
    