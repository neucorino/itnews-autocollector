import React, { useState } from 'react'
import type { RankedArticleResponse } from './types'
import { postArticleLike } from './api'

interface ArticleCardProps {
  article: RankedArticleResponse
}

export const ArticleCard: React.FC<ArticleCardProps> = ({ article }) => {
  const [liked, setLiked] = useState<boolean>(false)
  const [likeLoading, setLikeLoading] = useState<boolean>(false)

  // いいねボタンを押した時の処理
  const handleLike = async () => {
    if (likeLoading) return
    setLikeLoading(true)

    // 一旦表示を反転させる（楽観的UI更新）
    const newLikedState = !liked
    setLiked(newLikedState)

    // デフォルトユーザーID (1) で「いいね」APIを発行
    const success = await postArticleLike(article.id, 1, newLikedState)
    if (!success) {
      // 失敗した場合は元の状態に戻す
      setLiked(!newLikedState)
      alert('いいねの送信に失敗しました')
    }
    setLikeLoading(false)
  }

  return (
    <div
      style={{
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '16px',
        textAlign: 'left',
        backgroundColor: '#ffffff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
      }}
    >
      {/* 順位バッジとカテゴリ */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
        <span
          style={{
            fontWeight: 'bold',
            backgroundColor: '#333',
            color: '#fff',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '0.85em',
          }}
        >
          #{article.rank} 位
        </span>
        <span
          style={{
            fontSize: '0.8em',
            backgroundColor: '#e6f7ff',
            color: '#0050b3',
            border: '1px solid #91d5ff',
            padding: '2px 8px',
            borderRadius: '4px',
          }}
        >
          {article.category || 'IT'}
        </span>
        <span style={{ fontSize: '0.8em', color: '#888', marginLeft: 'auto' }}>
          {article.source}
        </span>
      </div>

      {/* 記事タイトル */}
      <h3 style={{ margin: '8px 0', fontSize: '1.1em', lineHeight: '1.4' }}>
        <a
          href={article.url}
          target="_blank"
          rel="noreferrer"
          style={{ color: '#1890ff', textDecoration: 'none' }}
        >
          {article.title}
        </a>
      </h3>

      {/* AI要約 (summary ➔ ai_summary に変更) */}
      <p style={{ color: '#444', fontSize: '0.9em', lineHeight: '1.5', margin: '12px 0' }}>
        {article.ai_summary}
      </p>

      {/* アクションエリア（いいねボタン & スコア表示） */}
      <div
        style={{
          display: 'flex',
        //   justify: 'space-between',
          alignItems: 'center',
          marginTop: '12px',
          borderTop: '1px solid #f0f0f0',
          paddingTop: '8px',
        }}
      >
        <button
          onClick={handleLike}
          disabled={likeLoading}
          style={{
            cursor: 'pointer',
            padding: '6px 16px',
            borderRadius: '20px',
            border: '1px solid ' + (liked ? '#ff4d4f' : '#d9d9d9'),
            backgroundColor: liked ? '#fff1f0' : '#ffffff',
            color: liked ? '#ff4d4f' : '#595959',
            fontWeight: liked ? 'bold' : 'normal',
            transition: 'all 0.2s',
          }}
        >
          {liked ? '❤️ いいね済み' : '👍 いいね'}
        </button>

        <span style={{ fontSize: '0.8em', color: '#8c8c8c' }}>
          スコア: {article.rank_score.toFixed(1)}点
        </span>
      </div>
    </div>
  )
}