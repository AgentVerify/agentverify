export async function ambiguousHelper(input: { value: string }) {
  return eval(input.value);
}
