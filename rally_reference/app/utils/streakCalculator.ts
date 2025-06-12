import { Match } from '../types';

interface PlayerStreak {
  playerName: string;
  currentStreak: number;
  maxStreak: number;
  lastMatchDate: string;
  series: string[];
}

export const calculateTennaquaStreaks = (matches: Match[]): PlayerStreak[] => {
  const playerStreaks = new Map<string, PlayerStreak>();
  
  // Process matches in chronological order
  const sortedMatches = [...matches].sort((a, b) => 
    new Date(a.Date).getTime() - new Date(b.Date).getTime()
  );

  for (const match of sortedMatches) {
    // Check if either team is a Tennaqua team
    const isTennaquaHome = match["Home Team"].startsWith("Tennaqua - ");
    const isTennaquaAway = match["Away Team"].startsWith("Tennaqua - ");
    
    if (!isTennaquaHome && !isTennaquaAway) {
      continue;
    }

    const series = isTennaquaHome ? 
      match["Home Team"].split(" - ")[1] : 
      match["Away Team"].split(" - ")[1];

    const players = isTennaquaHome 
      ? [match["Home Player 1"], match["Home Player 2"]]
      : [match["Away Player 1"], match["Away Player 2"]];
    
    const isWin = (isTennaquaHome && match.Winner === "home") || 
                 (!isTennaquaHome && match.Winner === "away");

    for (const player of players) {
      if (!playerStreaks.has(player)) {
        playerStreaks.set(player, {
          playerName: player,
          currentStreak: 0,
          maxStreak: 0,
          lastMatchDate: match.Date,
          series: [series]
        });
      }

      const streak = playerStreaks.get(player)!;
      
      // Update series if not already included
      if (!streak.series.includes(series)) {
        streak.series.push(series);
      }

      if (isWin) {
        streak.currentStreak++;
        streak.maxStreak = Math.max(streak.maxStreak, streak.currentStreak);
      } else {
        streak.currentStreak = 0;
      }
      streak.lastMatchDate = match.Date;
    }
  }

  // Convert to array and sort by max streak (descending), then by current streak
  return Array.from(playerStreaks.values())
    .sort((a, b) => {
      if (b.maxStreak !== a.maxStreak) {
        return b.maxStreak - a.maxStreak;
      }
      return b.currentStreak - a.currentStreak;
    });
}; 