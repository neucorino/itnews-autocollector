// ニュース記事の型定義（FastAPIのレスポンスに合わせる）
export interface Article {
    id: number
    title: string
    url: string
    summary: string
    published_at: string
    source: string
    importance?: number
    category?: string
}

  // ユーザー設定の型定義
export interface UserPreferences {
    categories: string[]
}