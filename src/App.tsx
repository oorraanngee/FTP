import React, { useState, useEffect } from 'react';
import { MacWindow } from './components/MacWindow';
import { Download, Terminal, Info } from 'lucide-react';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';

const fileImports = import.meta.glob('/public/FPT/*/*', { as: 'raw' });
const VERSION_FILES: Record<string, string[]> = {};

Object.keys(fileImports).forEach(path => {
  const match = path.match(/\/public\/FPT\/(v\d+\.\d+)\/(.*)/);
  if (match) {
    const version = match[1];
    const file = match[2];
    if (!VERSION_FILES[version]) {
      VERSION_FILES[version] = [];
    }
    if (file !== '.keep') {
      VERSION_FILES[version].push(file);
    }
  }
});

const VERSIONS = Object.keys(VERSION_FILES).sort((a, b) => {
  const aNum = parseFloat(a.replace('v', ''));
  const bNum = parseFloat(b.replace('v', ''));
  return bNum - aNum;
});

export default function App() {
  const [selectedVersion, setSelectedVersion] = useState<string>(VERSIONS[0] || 'v7.0');
  const [isDownloading, setIsDownloading] = useState(false);
  const [latestVersion, setLatestVersion] = useState<string | null>(null);

  useEffect(() => {
    fetch("https://firestore.googleapis.com/v1/projects/fix-this-python/databases/(default)/documents/app_info/version")
      .then(res => res.json())
      .then(data => {
        const version = data.fields?.latest?.stringValue;
        if (version) {
          setLatestVersion(version);
        }
      })
      .catch(err => console.error("Failed to fetch latest version:", err));
  }, []);

  const handleDownload = async (version: string) => {
    const files = VERSION_FILES[version];
    if (files.length === 0) {
      alert(`В версии ${version} нет файлов для скачивания (пустая версия).`);
      return;
    }

    setIsDownloading(true);
    try {
      const zip = new JSZip();
      const folder = zip.folder(`FTP_${version}`);

      for (const file of files) {
        const url = `/FPT/${version}/${file}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Не удалось скачать ${file}`);
        const content = await response.text();
        folder?.file(file, content);
      }

      const content = await zip.generateAsync({ type: 'blob' });
      saveAs(content, `FTP_${version}.zip`);
    } catch (error) {
      console.error(error);
      alert('Произошла ошибка при скачивании версии.');
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="min-h-screen osx-bg font-sans text-gray-800 selection:bg-blue-300">
      {/* Modern Header */}
      <header className="w-full pt-16 pb-12 px-6 flex flex-col items-center justify-center text-white text-center">
        <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight drop-shadow-xl" style={{ textShadow: '0 2px 4px rgba(0,0,0,0.4)' }}>
          Fix This Python
        </h1>
        <p className="text-lg md:text-xl text-blue-100 max-w-2xl drop-shadow-md">
          Современная утилита для автоматического исправления синтаксических ошибок в вашем Python-коде.
        </p>
      </header>

      <main className="max-w-5xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start">
          
          {/* Left Column - Main Content & Description */}
          <div className="lg:col-span-7 flex flex-col gap-10">
            
            {/* About Window */}
            <MacWindow title="About FTP">
              <div className="p-8">
                <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
                  <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-gray-100 to-gray-300 border border-gray-400 shadow-inner flex items-center justify-center flex-shrink-0">
                    <Terminal size={48} className="text-gray-700" strokeWidth={1.5} />
                  </div>
                  <div className="text-center sm:text-left">
                    <h2 className="text-2xl font-bold mb-3 text-gray-900 tracking-tight">Что такое FTP?</h2>
                    <p className="text-[#444] mb-5 leading-relaxed text-[15px]">
                      <strong>Fix This Python (FTP)</strong> — это умный консольный инструмент, созданный для помощи начинающим программистам. 
                      Он сканирует ваш исходный код на наличие распространенных опечаток, таких как забытые двоеточия, ошибки в функции <code>print</code>, и операторы из других ЯП.
                    </p>
                    
                    <div className="bg-[#f8f9fa] p-5 rounded-xl border border-gray-200">
                      <h3 className="font-semibold text-xs mb-3 text-gray-500 uppercase tracking-wider">Ключевые возможности</h3>
                      <ul className="list-none text-sm text-gray-700 space-y-2">
                        <li className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                          Эвристический поиск опечаток в <code>print()</code>
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                          Умная расстановка забытых двоеточий
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                          Автозамена <code>elsif</code> на <code>elif</code>
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                          Интерактивный режим подтверждения
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </MacWindow>

            {/* Latest Version Window */}
            <MacWindow title="Updates & Partners">
              <div className="p-6 bg-white flex flex-col gap-6">
                <div className="flex items-start gap-5">
                  <div className="p-3 bg-blue-50 text-blue-500 rounded-xl shadow-sm flex-shrink-0">
                    <Info size={28} />
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900 text-lg mb-1.5">Обновления</h3>
                    {latestVersion ? (
                      <p className="text-[#444] text-[15px] leading-relaxed">
                        {VERSIONS.includes(latestVersion) ? (
                          <>Последняя версия <span className="font-bold text-blue-600">{latestVersion}</span>.</>
                        ) : (
                          <>Последняя версия <span className="font-bold text-blue-600">{latestVersion}</span>. В данный момент версии на сайте нету, подождите пока она появится.</>
                        )}
                      </p>
                    ) : (
                      <p className="text-gray-500 text-sm italic">Проверка версий...</p>
                    )}
                  </div>
                </div>

                <div className="w-full h-px bg-gray-100"></div>

                <div className="flex items-start gap-5">
                  <div className="p-3 bg-purple-50 text-purple-500 rounded-xl shadow-sm flex-shrink-0">
                    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-gray-900 text-lg mb-1.5">Партнёры — B10</h3>
                    <p className="text-[#444] text-[15px] leading-relaxed">
                      <a href="https://base-4096.vercel.app/" target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:text-purple-700 font-semibold underline underline-offset-2">
                        B10 (Base-4096)
                      </a> — это позиционная 4096-ричная система. 1 символ = 12 бит данных. Любой RGB цвет (16 миллионов оттенков) записывается ровно двумя символами! Имеет Python, Npm, Cdn библиотеки.
                    </p>
                  </div>
                </div>
              </div>
            </MacWindow>

          </div>

          {/* Right Column - Downloads */}
          <div className="lg:col-span-5 sticky top-8">
            <MacWindow title="Downloads">
              <div className="p-7 flex flex-col gap-6 bg-[#fbfbfb]">
                <div>
                  <h3 className="font-bold text-lg mb-4 text-gray-900 tracking-tight">Доступные версии</h3>
                  <div className="flex flex-col gap-2.5">
                    {VERSIONS.map(v => (
                      <div 
                        key={v}
                        onClick={() => setSelectedVersion(v)}
                        className={`px-4 py-3 rounded-xl border flex items-center justify-between cursor-pointer transition-all duration-200 ${
                          selectedVersion === v 
                            ? 'bg-blue-50 border-blue-400 shadow-[0_2px_10px_rgba(59,130,246,0.15)] scale-[1.02]' 
                            : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-sm'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-1.5 rounded-lg ${selectedVersion === v ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-500'}`}>
                            <Terminal size={18} strokeWidth={selectedVersion === v ? 2.5 : 2} />
                          </div>
                          <span className={`font-semibold ${selectedVersion === v ? 'text-blue-900' : 'text-gray-700'}`}>
                            Утилита FTP {v}
                          </span>
                        </div>
                        {VERSION_FILES[v].length === 0 && (
                          <span className="text-xs px-2.5 py-1 bg-gray-100 text-gray-500 rounded-full font-medium">
                            Пусто
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="h-px w-full bg-gradient-to-r from-transparent via-gray-200 to-transparent my-1"></div>

                <div className="flex flex-col gap-4">
                  <div className="text-center">
                    <p className="text-[13px] text-gray-500 mb-0.5 uppercase tracking-wider font-semibold">Выбрано</p>
                    <p className="text-3xl font-bold text-gray-900 tracking-tight">{selectedVersion}</p>
                    <p className="text-sm text-gray-500 mt-1">
                      Файлов: {VERSION_FILES[selectedVersion].length}
                    </p>
                  </div>
                  
                  <button
                    onClick={() => handleDownload(selectedVersion)}
                    disabled={isDownloading}
                    className="aqua-blue-button w-full py-3.5 px-4 font-bold text-[15px] flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group tracking-wide mt-2"
                  >
                    <Download size={18} className={isDownloading ? 'animate-bounce' : 'group-hover:translate-y-0.5 transition-transform'} />
                    {isDownloading ? 'Архивация...' : `Скачать ${selectedVersion}`}
                  </button>
                </div>
              </div>
            </MacWindow>
          </div>

        </div>
      </main>
    </div>
  );
}
