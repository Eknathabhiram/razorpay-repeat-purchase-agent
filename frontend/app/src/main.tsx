import React from 'react';
import {createRoot} from 'react-dom/client';
import {HashRouter} from 'react-router';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import App from './app/App';
import ErrorBoundary from './components/ErrorBoundary';
import './styles/base.css';
import './styles/app.css';
import './styles/production.css';
import './styles/merchant.css';
import './styles/avime.css';
const queryClient=new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:false},mutations:{retry:false,networkMode:'always'}}});
createRoot(document.getElementById('root')!).render(
  <React.StrictMode><ErrorBoundary><QueryClientProvider client={queryClient}><HashRouter><App/></HashRouter></QueryClientProvider></ErrorBoundary></React.StrictMode>
);
