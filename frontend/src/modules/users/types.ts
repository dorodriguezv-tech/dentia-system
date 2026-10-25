export type { UserWithRoleOut } from '../auth/types'

export interface ClinicAssignmentInput {
  clinic_id: string
  default_resource_id?: string | null
}

export interface CreateUserInput {
  email: string
  full_name: string
  password: string
  role_code: string
  professional_license?: string | null
  default_resource_id?: string | null
  additional_clinics?: ClinicAssignmentInput[]
}

export interface UpdateUserInput {
  full_name?: string
  email?: string
  is_active?: boolean
  role_code?: string
  professional_license?: string | null
  new_password?: string
}
