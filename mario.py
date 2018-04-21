# Import the module
from cs50 import get_float
from cs50 import get_int
from cs50 import get_string

a = get_int
while True:
    if a > 0:
        break


for i in range(1 ,a):
    print(" "*(a-i))
    print("#"*i,end="")
    print()