import React from 'react';

const Navbar = ({ currentPage, setCurrentPage, betSlipCount, setBetSlipOpen }) => {
  const navItems = [
    { key: 'home', label: 'Sports' },
    { key: 'rank', label: 'Leaderboard' },
    { key: 'bets', label: 'My Bets' }
  ];

  return (
    <nav className="bg-white shadow-lg border-b sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <button 
              onClick={() => setCurrentPage('home')}
              className="text-2xl font-bold text-blue-600"
            >
              🎯 SportsBook
            </button>
          </div>
          <div className="flex items-center space-x-8">
            {navItems.map((item) => (
              <button
                key={item.key}
                onClick={() => setCurrentPage(item.key)}
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentPage === item.key
                    ? 'text-blue-600 bg-blue-50'
                    : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50'
                }`}
              >
                {item.label}
              </button>
            ))}
            
            {/* Bet Slip Button */}
            <button
              onClick={() => setBetSlipOpen(true)}
              className="relative bg-green-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 transition-colors"
            >
              Bet Slip
              {betSlipCount > 0 && (
                <span className="absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                  {betSlipCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;