import React from 'react'
import type { Article } from './types'

interface ArticleCardProps {
  article: Article
}

export const ArticleCard: React.FC<ArticleCardProps> = ({ article }) => {
  return (
    <div style={{
      border: '1px solid #ccc',
      borderRadius: '8px',
      padding: '16px',
      marginBottom: '12px',
      textAlign: 'left',
      backgroundColor: '#f9f9f9'
    }}>
      <span style={{
        fontSize: '0.8em',
        backgroundColor: '#0070f3',
        color: '#fff',
        padding: '2px 8px',
        borderRadius: '4px'
      }}>
        {article.category || 'IT'}
      </span>
      <h3 style={{ margin: '8px 0', color: '#333' }}>
        <a href={article.url} target="_blank" rel="noreferrer">
          {article.title}
        </a>
      </h3>
      <p style={{ color: '#666', fontSize: '0.9em' }}>{article.summary}</p>
      <button style={{ cursor: 'pointer', padding: '6px 12px' }}>
        👍 いいね
      </button>
    </div>
  )
}