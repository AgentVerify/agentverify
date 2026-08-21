const axios = { get: async (_url: string) => ({}) };

export async function ordinary(url: string) {
  return await axios.get(url);
}
