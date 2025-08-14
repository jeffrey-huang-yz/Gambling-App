import React, { useState } from 'react';
import './App.css';
import Navbar from './components/Navbar';
import HomePage from './components/HomePage';
import RankPage from './components/RankPage';
import BetsPage from './components/BetsPage';

const App = () => {
  const [currentPage, setCurrentPage] = useState('home');

  const renderPage = () => {
    switch(currentPage) {
      case 'home':
        return <HomePage />;
      case 'rank':
        return <RankPage />;
      case 'bets':
        return <BetsPage />;
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar currentPage={currentPage} setCurrentPage={setCurrentPage} />
      {renderPage()}
    </div>
  );
};

export default App;