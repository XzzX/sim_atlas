import flowrep as fr


@fr.atomic("sum")
def add(a: float, b: float) -> float:
    """Returns the sum of a and b."""
    return a + b


@fr.atomic("product")
def mul(a: float, b: float) -> float:
    """Returns the product of a and b."""
    return a * b


@fr.workflow
def linear(x: float, slope: float, intercept: float) -> float:
    """y = slope * x + intercept"""
    scaled = mul(x, slope)  # type: ignore
    result = add(scaled, intercept)  # type: ignore
    return result  # type: ignore

run_1 = fr.tools.run_recipe(linear.flowrep_recipe, x=-1.3, slope=-5, intercept=2.1)
run_2 = fr.tools.run_recipe(linear.flowrep_recipe, x=3.1, slope=2, intercept=0)
run_3 = fr.tools.run_recipe(linear.flowrep_recipe, x=81.0, slope=9, intercept=-1.1)

