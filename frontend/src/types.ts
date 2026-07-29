// ニュース記事の型定義（FastAPIのレスポンスに合わせる）
export interface RankedArticleResponse {
    id: number
    title: string
    url: string
    source: string
    ai_summary: string
    importance?: number
    category?: string
    rank:number
    rank_score:number
    published_at: string
}

  // ユーザー設定の型定義
export interface UserPreferencesRequest {
    user_id:number
    categories:string[]
}

export interface ArticleLikeRequest{
    user_id:number
    is_liked:boolean
}