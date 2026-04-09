import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const rules = [
      { source: '/graphql', destination: 'http://127.0.0.1:8001/graphql' },
      { source: '/api/:path*', destination: 'http://127.0.0.1:8001/api/:path*' },
    ]
    if (process.env.NODE_ENV !== 'production') {
      rules.push({ source: '/graphiql', destination: 'http://127.0.0.1:8001/graphiql' })
    }
    return rules
  },
}

export default nextConfig
