import { FileQuestion } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState, PageHeader } from '@/components'
import { buttonVariants } from '@/components/ui/button'

export default function NotFoundPage() {
  return (
    <>
      <PageHeader title="Page not found" />
      <EmptyState
        icon={<FileQuestion />}
        title="There is no page at this address"
        description="Check the link, or go to the data health page of the latest run."
        action={
          <Link to="/runs/latest/health" className={buttonVariants({ size: 'sm' })}>
            Open the latest run
          </Link>
        }
      />
    </>
  )
}
