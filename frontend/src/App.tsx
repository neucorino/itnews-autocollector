import { useState, useEffect } from 'react'
import './App.css'
import { ArticleCard } from './ArticleCard'
import type { RankedArticleResponse } from './types'
import { fetchRankedArticles } from './api'

function App() {
  const [articles, setArticles] = useState<RankedArticleResponse[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  // ※ バックエンド起動時はコメントアウトを解除してAPI通信できます
  useEffect(() => {
    const loadArticles = async () => {
      setLoading(true)
      const data = await fetchRankedArticles()
      if (data.length > 0) {
        setArticles(data)
      }
      setLoading(false)
    }
    loadArticles()
  }, [])


  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ textAlign: 'center', color: '#fff' }}>IT News Collector 🚀</h1>
      <p style={{ textAlign: 'center', color: '#999', marginBottom: '24px' }}>
        AIが厳選した最新のITニュース
      </p>

      {loading ? (
        <p>記事を読み込み中...</p>
      ) : articles.length === 0 ? (
        <p>表示できるニュースがありません。</p>
      ) : (
        articles.map((article) => <ArticleCard key={article.id} article={article} />)
      )}
    </div>
  )
}

export default App