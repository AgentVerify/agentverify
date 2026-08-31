export async function importedCalculate(input: {
  expression: string;
}): Promise<{ result: number }> {
  return new Function(`return (${input.expression})`)();
}

export async function shared(input: { value: string }) {
  return eval(input.value);
}
