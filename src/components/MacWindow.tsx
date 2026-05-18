import React from 'react';

interface MacWindowProps {
  title: string;
  children: React.ReactNode;
}

export function MacWindow({
  title,
  children,
}: MacWindowProps) {
  return (
    <div className="flex flex-col bg-white rounded-t-xl rounded-b-lg overflow-hidden aqua-window w-full transition-transform hover:scale-[1.01] duration-300 relative group">
      {/* Aqua Title Bar */}
      <div className="relative flex items-center justify-center px-4 py-1 h-7 border-b border-gray-400 aqua-titlebar">
        <div className="absolute inset-0 aqua-pinstripes pointer-events-none opacity-40"></div>
        
        {/* Window Controls */}
        <div className="absolute left-2.5 flex items-center gap-1.5 z-10">
          <div className="w-3.5 h-3.5 rounded-full bg-gradient-to-b from-[#ff8579] to-[#f73527] border border-[#d2160d] shadow-sm shadow-[#ff7a72]/30"></div>
          <div className="w-3.5 h-3.5 rounded-full bg-gradient-to-b from-[#ffd35b] to-[#fbb019] border border-[#d79409] shadow-sm shadow-[#ffcd4f]/30"></div>
          <div className="w-3.5 h-3.5 rounded-full bg-gradient-to-b from-[#4cd961] to-[#25ad36] border border-[#169426] shadow-sm shadow-[#40db57]/30"></div>
        </div>

        {/* Title */}
        <div className="font-lucida text-[13px] font-semibold tracking-normal text-gray-800 drop-shadow-sm z-10 select-none drop-shadow-[0_1px_1px_rgba(255,255,255,0.8)]">
          {title}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 bg-white overflow-hidden">
        {children}
      </div>
    </div>
  );
}
