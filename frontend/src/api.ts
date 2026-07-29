import type { RankedArticleResponse, UserPreferencesRequest, ArticleLikeRequest } from './types'

const API_BASE_URL = 'http://localhost:8080/v1'

// 1. ランキング記事一覧の取得
export const fetchRankedArticles = async (): Promise<RankedArticleResponse[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/rankings`)
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    const data: RankedArticleResponse[] = await response.json()
    return data
  } catch (error) {
    console.error('ニュースの取得に失敗しました:', error)
    return []
  }
}

// 2. 記事への「いいね」送信 (v1.4.0 対応)
export const postArticleLike = async (
  articleId: number,
  userId: number,
  isLiked: boolean
): Promise<boolean> => {
  try {
    const payload: ArticleLikeRequest = {
      user_id: userId,
      is_liked: isLiked,
    }
    const response = await fetch(`${API_BASE_URL}/articles/${articleId}/like`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    return response.ok
  } catch (error) {
    console.error('いいねの送信に失敗しました:', error)
    return false
  }
}

// 3. ユーザーの興味分野（カテゴリ）の一括保存 (v1.4.0 対応)
export const saveUserPreferences = async (
  userId: number,
  categories: string[]
): Promise<boolean> => {
  try {
    const payload: UserPreferencesRequest = {
      user_id: userId,
      categories: categories,
    }
    const response = await fetch(`${API_BASE_URL}/users/preferences`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
    return response.ok
  } catch (error) {
    console.error('ユーザー設定の保存に失敗しました:', error)
    return false
  }
}