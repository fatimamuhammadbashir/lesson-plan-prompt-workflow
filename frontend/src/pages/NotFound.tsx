import { Link } from 'react-router-dom'
import { ArrowLeft, Compass } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="empty-panel not-found-panel">
      <span className="empty-icon">
        <Compass size={30} />
      </span>
      <h3>This page is not in the lesson plan.</h3>
      <p>The route does not exist. Return to the workspace to continue reviewing drafts.</p>
      <Link to="/" className="button button-primary">
        <ArrowLeft size={16} /> Back to dashboard
      </Link>
    </div>
  )
}
