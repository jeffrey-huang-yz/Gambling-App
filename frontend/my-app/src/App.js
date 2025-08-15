import React, { useState } from 'react';
import './index.css';
import { sampleBetHistory } from './data/sportsData';
import Navbar from './components/Navbar';
import HomePage from './components/HomePage';
import BetsPage from './components/BetsPage';
import RankPage from './components/RankPage';
import BetSlipSidebar from './components/BetSlipSidebar';

const App = () => {
  const [currentPage, setCurrentPage] = useState('home');
  const [betSlip, setBetSlip] = useState([]);
  const [betSlipOpen, setBetSlipOpen] = useState(false);
  const [betHistory, setBetHistory] = useState(sampleBetHistory);

  const addToBetSlip = (bet) => {
    if (!betSlip.find(existing => existing.id === bet.id)) {
      setBetSlip([...betSlip, { ...bet, amount: 0 }]);
    }
  };

  const updateBetAmount = (betId, amount) => {
    setBetSlip(betSlip.map(bet => 
      bet.id === betId ? { ...bet, amount } : bet
    ));
  };

  const removeBet = (betId) => {
    setBetSlip(betSlip.filter(bet => bet.id !== betId));
  };

  const clearBetSlip = () => {
    setBetSlip([]);
  };

  const placeBets = (bets, betType) => {
    // Add placed bets to history
    const newBets = bets
      .filter(bet => bet.amount > 0)
      .map(bet => ({
        id: `placed-${Date.now()}-${bet.id}`,
        game: bet.game,
        type: betType === 'parlay' ? 'Parlay' : bet.type,
        selection: betType === 'parlay' ? `${bets.length} leg parlay` : bet.selection,
        odds: bet.odds,
        amount: bet.amount,
        status: 'active',
        placedAt: new Date().toLocaleString(),
        potentialWin: bet.amount * (bet.odds.startsWith('+') ? 
          parseInt(bet.odds.slice(1)) / 100 : 
          100 / parseInt(bet.odds.slice(1)))
      }));

    setBetHistory([...newBets, ...betHistory]);
    clearBetSlip();
    alert(`${betType === 'parlay' ? 'Parlay' : 'Straight'} bet${newBets.length > 1 ? 's' : ''} placed successfully!`);
  };

  const renderPage = () => {
    switch(currentPage) {
      case 'home':
        return (
          <HomePage 
            addToBetSlip={addToBetSlip}
            betSlipOpen={betSlipOpen}
            setBetSlipOpen={setBetSlipOpen}
            betSlip={betSlip}
            updateBetAmount={updateBetAmount}
            removeBet={removeBet}
            clearBetSlip={clearBetSlip}
            onPlaceBets={placeBets}
          />
        );
      case 'rank':
        return <RankPage />;
      case 'bets':
        return <BetsPage betHistory={betHistory} />;
      default:
        return (
          <HomePage 
            addToBetSlip={addToBetSlip}
            betSlipOpen={betSlipOpen}
            setBetSlipOpen={setBetSlipOpen}
            betSlip={betSlip}
            updateBetAmount={updateBetAmount}
            removeBet={removeBet}
            clearBetSlip={clearBetSlip}
            onPlaceBets={placeBets}
          />
        );
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar 
        currentPage={currentPage} 
        setCurrentPage={setCurrentPage}
        betSlipCount={betSlip.length}
        setBetSlipOpen={setBetSlipOpen}
      />
      {renderPage()}
      
      <BetSlipSidebar
        isOpen={betSlipOpen}
        onClose={() => setBetSlipOpen(false)}
        betSlip={betSlip}
        updateBetAmount={updateBetAmount}
        removeBet={removeBet}
        clearBetSlip={clearBetSlip}
        onPlaceBets={placeBets}
      />
    </div>
  );
};

export default App;