export async function ordinary(nodeData: { inputs?: { url?: string } }) {
  const requestConfig = { url: nodeData.inputs?.url }
  return await secureAxiosRequest(requestConfig)
}

async function secureAxiosRequest(_config: object) {
  return {}
}
