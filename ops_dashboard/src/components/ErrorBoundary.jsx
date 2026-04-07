import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error) {
    console.error('Panel render failed', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, color: '#ffb347', fontSize: 14 }}>
          {this.props.fallbackText || 'A panel failed to render. Please refresh.'}
        </div>
      )
    }
    return this.props.children
  }
}
