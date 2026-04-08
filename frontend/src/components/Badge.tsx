import type { Finding } from '../types'

const priorityClasses: Record<Finding['priority'], string> = {
  CRITICAL: 'bg-red-100 text-red-700 border border-red-200',
  HIGH: 'bg-orange-100 text-orange-700 border border-orange-200',
  COALITION: 'bg-purple-100 text-purple-700 border border-purple-200',
  EVIDENCE: 'bg-blue-100 text-blue-700 border border-blue-200',
  MEDIUM: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
  LOW: 'bg-gray-100 text-gray-500 border border-gray-200',
}

interface Props {
  priority: Finding['priority']
}

export default function Badge({ priority }: Props) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${priorityClasses[priority]}`}>
      {priority}
    </span>
  )
}
