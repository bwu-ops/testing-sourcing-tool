import { NextPageWithLayout } from '@/pages/_app'
import DefaultPageContainer from '@/components/layouts/DefaultPageContainer'
import SourcingDashboard from '@/components/sourcing/SourcingDashboard'

const Home: NextPageWithLayout = () => <SourcingDashboard />

Home.getLayout = (page) => (
  <DefaultPageContainer title="Talent Mapping">{page}</DefaultPageContainer>
)

export default Home
