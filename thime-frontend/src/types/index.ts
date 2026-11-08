// ─── 기록 (F1·F2·F3) ───────────────────────────────────────────
export interface Followup {
  text: string
  addedAt: string
}

export interface Record {
  userId: string
  recordId: string
  rawText: string
  summaryLine: string
  tags: string[]
  followups: Followup[]
  audioS3Key: string
  isProcessed: boolean
  createdAt: string
  updatedAt: string
}

// ─── 질문 (F4) ─────────────────────────────────────────────────
export interface Question {
  date: string
  questionId: string
  content: string
  isDefault: boolean
  createdAt: string
}

// ─── 피드·답변 (F5) ────────────────────────────────────────────
export interface Feed {
  questionId: string
  answererUserId: string   // 댓글 라우팅용
  userId: string | null    // 익명이면 null
  answerText: string
  createdAt: string
}

export interface MyAnswer {
  answerText: string
  createdAt: string
  isPublic: boolean
}

export interface FeedListResponse {
  locked: boolean
  message?: string
  feeds: Feed[]
  myAnswer: MyAnswer | null
  count: number
}

// ─── 댓글·버블 ─────────────────────────────────────────────────
export type CommentRole = 'answerer' | 'commenter'

export interface Comment {
  commentId: string
  commenterUserId?: string   // answerer 입장에서만 노출
  commentText: string
  hasReply?: boolean
  hasReplied?: boolean
  replyText: string | null
  repliedAt: string | null
  isRead?: boolean
  createdAt: string
}

export interface CommentsResponse {
  role: CommentRole
  comments: Comment[]
  unreadCount?: number
  totalCount: number
}

// ─── API 공통 ──────────────────────────────────────────────────
export interface ApiError {
  error: string
}
