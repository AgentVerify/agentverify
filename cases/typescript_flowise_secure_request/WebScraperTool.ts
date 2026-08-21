import { secureFetch } from './index'

class Tool {}

class WebScraperRecursiveTool extends Tool {
  name = 'web_scraper_tool'

  private async scrapeSingleUrl(url: string) {
    return await secureFetch(url, { redirect: 'follow', follow: 5 })
  }

  private async scrapeRecursive(url: string, currentDepth: number): Promise<object[]> {
    if (currentDepth > 1) return []
    const result = await this.scrapeSingleUrl(url)
    return [result]
  }

  async _call(initialInput: string): Promise<string> {
    const result = await this.scrapeRecursive(initialInput, 1)
    return JSON.stringify(result)
  }
}

export { WebScraperRecursiveTool }
