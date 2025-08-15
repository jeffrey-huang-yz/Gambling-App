// Sample sports data
export const sportsData = {
    nfl: {
      name: 'NFL',
      icon: '🏈',
      games: [
        {
          id: 1,
          team1: 'Kansas City Chiefs',
          team2: 'Buffalo Bills',
          time: 'Today 8:15 PM',
          spread1: { team: 'KC', line: '-2.5', odds: '-110' },
          spread2: { team: 'BUF', line: '+2.5', odds: '-110' },
          moneyline1: { team: 'KC', odds: '-130' },
          moneyline2: { team: 'BUF', odds: '+110' },
          total: { over: '-110', under: '-110', points: '47.5' }
        },
        {
          id: 2,
          team1: 'Dallas Cowboys',
          team2: 'Philadelphia Eagles',
          time: 'Tomorrow 1:00 PM',
          spread1: { team: 'DAL', line: '+3.5', odds: '-110' },
          spread2: { team: 'PHI', line: '-3.5', odds: '-110' },
          moneyline1: { team: 'DAL', odds: '+150' },
          moneyline2: { team: 'PHI', odds: '-175' },
          total: { over: '-105', under: '-115', points: '52.5' }
        }
      ]
    },
    nba: {
      name: 'NBA',
      icon: '🏀',
      games: [
        {
          id: 3,
          team1: 'Los Angeles Lakers',
          team2: 'Boston Celtics',
          time: 'Tonight 9:00 PM',
          spread1: { team: 'LAL', line: '+4.5', odds: '-110' },
          spread2: { team: 'BOS', line: '-4.5', odds: '-110' },
          moneyline1: { team: 'LAL', odds: '+165' },
          moneyline2: { team: 'BOS', odds: '-195' },
          total: { over: '-110', under: '-110', points: '228.5' }
        }
      ]
    },
    mlb: {
      name: 'MLB',
      icon: '⚾',
      games: [
        {
          id: 4,
          team1: 'New York Yankees',
          team2: 'Houston Astros',
          time: 'Today 7:05 PM',
          spread1: { team: 'NYY', line: '+1.5', odds: '-150' },
          spread2: { team: 'HOU', line: '-1.5', odds: '+130' },
          moneyline1: { team: 'NYY', odds: '+120' },
          moneyline2: { team: 'HOU', odds: '-140' },
          total: { over: '-105', under: '-115', points: '8.5' }
        }
      ]
    }
  };
  
  // Sample bet history data
  export const sampleBetHistory = [
    {
      id: 'bet1',
      game: 'Chiefs vs Bills',
      type: 'Moneyline',
      selection: 'Kansas City Chiefs',
      odds: '-130',
      amount: 50,
      status: 'active',
      placedAt: '2025-08-14 14:30',
      potentialWin: 38.46
    },
    {
      id: 'bet2',
      game: 'Lakers vs Celtics',
      type: 'Spread',
      selection: 'Lakers +4.5',
      odds: '-110',
      amount: 25,
      status: 'won',
      placedAt: '2025-08-13 19:45',
      potentialWin: 22.73,
      result: 47.73
    },
    {
      id: 'bet3',
      game: 'Cowboys vs Eagles Parlay',
      type: 'Parlay',
      selection: 'Cowboys ML + Over 52.5',
      odds: '+285',
      amount: 20,
      status: 'lost',
      placedAt: '2025-08-12 16:20',
      potentialWin: 57.00,
      result: 0
    }
  ];