try:
    print(__file__)
    with open("test.py", "w") as f:
        f.write("Hello")
except Exception as e:
    print(e)
