export type { UserWithRoleOut } from '../auth/types'

export interface CreateUserInput {
  email: string
  full_name: string
  password: string
  role_code: string
}

export interface UpdateUserInput {
  full_name?: string
  is_active?: boolean
  role_code?: string
}
