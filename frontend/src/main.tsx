import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/montserrat/600.css'
import '@fontsource/montserrat/700.css'
import './theme/tokens.css'
import './index.css'
import { AppProviders } from './app/providers'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppProviders />
  </StrictMode>,
)
