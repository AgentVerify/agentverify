class Calculator:
    def evaluate(self, expression: str):
        return expression


def ordinary_evaluate(calculator: Calculator, expression: str):
    return calculator.evaluate(expression)
