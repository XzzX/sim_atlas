import marimo

__generated_with = "0.19.6"
app = marimo.App()


@app.cell
def _():
    # magic command not supported in marimo; please file an issue to add support
    # %load_ext autoreload
    # '%autoreload 2' command supported automatically in marimo
    import os
    os.environ['ANYWIDGET_HMR'] = '1'
    return


@app.cell
def _():
    from simflow import Widget
    w = Widget()
    w
    return (w,)


@app.cell
def _(w):
    w.nodes
    return


@app.cell
def _():
    def add(a, b, / , c, d, *, e, f):
        pass

    print(add.__code__.co_)
    return (add,)


@app.cell
def _(add):
    import inspect
    sig = inspect.signature(add)
    for s in sig:
        print(s)
    return


@app.function
def fib(n):
    def fib_tuple(n):
        """Returns a tuple of the (n-1)-th and the n-th Fibonacci number."""
        return (0,0) if n < 1 else ((0,1) if n < 2 else fib_tuple(n-1))
        match n:
            case 0: return (0,0)
            case 1: return (0,1)
            case _:
                ft = fib_tuple(n-1)
                return (ft[1], ft[0] + ft[1])
    return fib_tuple(n)[1]


@app.cell
def _():
    for n in range(10):
        print(fib(n))
    return


@app.cell
def _():
    def fib_tuple(n):
        def recurse():
            ft = fib_tuple(n-1)
            return (ft[1], ft[0] + ft[1])

        def ternary_2():
            return (0,1) if n < 2 else recurse()

        def ternary_1():
            return (0,0) if n < 1 else ternary_2()

        return ternary_1()

    for i in range(10):
        print(fib_tuple(i)[1])
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
