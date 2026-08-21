import { secureAxiosRequest } from './httpSecurity'

type INodeData = { inputs?: { url?: string } }
type AxiosRequestConfig = Record<string, unknown>

interface INode {}

class HTTP_Agentflow implements INode {
  name: string
  inputs = [
    {
      name: 'url',
      type: 'string',
      acceptVariable: true,
    },
  ]

  constructor() {
    this.name = 'httpAgentflow'
  }

  async run(nodeData: INodeData) {
    const url = nodeData.inputs?.url as string
    const queryString = ''
    const finalUrl = queryString ? `${url}${url.includes('?') ? '&' : '?'}${queryString}` : url
    const requestConfig: AxiosRequestConfig = {
      method: 'GET',
      url: finalUrl,
      headers: {},
    }
    return await secureAxiosRequest(requestConfig)
  }
}

module.exports = { nodeClass: HTTP_Agentflow }
