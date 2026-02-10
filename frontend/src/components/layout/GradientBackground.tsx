import React from 'react';

export const GradientBackground = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#ffe4d6] via-[#fbd0e4] to-[#dbe4ff]">
      {children}
    </div>
  );
};
