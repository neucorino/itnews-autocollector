import { useState, useEffect } from 'react'
import './App.css'
import { ArticleCard } from './ArticleCard'
import type { RankedArticleResponse } from './types'
import { fetchRankedArticles } from './api'

// バックエンドから届く想定の新しいダミーデータ
const dummyArticle: RankedArticleResponse = {
  id: 101,
  title: 'FastAPI + Reactで構築する最新Webアプリ開発ロードマップ',
  url: 'https://example.com',
  source: 'GitHub Blog',
  ai_summary:
    'FastAPIの型安全なREST APIと、React+TypeScriptのコンポーネント指向UIを連携させる実践的な手法を解説しています。',
  importance: 9,
  category: 'Web開発',
  rank: 1,
  rank_score: 8.8,
  published_at: '2026-07-29',
}

function App() {
  const [articles, setArticles] = useState<RankedArticleResponse[]>([dummyArticle])
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