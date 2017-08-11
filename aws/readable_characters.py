READABLE_CHARACTERS = list('23456789BCDEGHJKMNPRSTUVWXYZ')

from random import sample

def readable_characters(length):
    return ''.join(sample(READABLE_CHARACTERS,length))

