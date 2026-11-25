
import Svg, { Circle, Path, Rect } from 'react-native-svg';

export type NomeIcone =
  | 'inicio'
  | 'pacientes'
  | 'novo-paciente'
  | 'avaliacao'
  | 'perfil'
  | 'ajuda'
  | 'livro'
  | 'olho'
  | 'olho-fechado'
  | 'email'
  | 'cadeado'
  | 'seta'
  | 'escudo'
  | 'camera'
  | 'imagem'
  | 'editar'
  | 'pesquisa'
  | 'arquivo'
  | 'sair'
  | 'confirmar';

type Props = {
  nome: NomeIcone;
  tamanho?: number;
  cor?: string;
};

export default function IconeInterface({
  nome,
  tamanho = 24,
  cor = '#005088',
}: Props) {
  const desenhos: Record<NomeIcone, React.ReactNode> = {
    inicio: (
      <>
        <Path d="M3 10 12 3l9 7" />
        <Path d="M5 9v12h5v-7h4v7h5V9" />
      </>
    ),

    pacientes: (
      <>
        <Circle cx="9" cy="7" r="3" />
        <Path d="M3 20v-2a6 6 0 0 1 12 0v2" />
        <Path d="M16 4a3 3 0 0 1 0 6" />
        <Path d="M17 13a5 5 0 0 1 4 5v2" />
      </>
    ),

    'novo-paciente': (
      <>
        <Circle cx="9" cy="7" r="4" />
        <Path d="M2 21v-2a7 7 0 0 1 14 0v2" />
        <Path d="M19 8v6M16 11h6" />
      </>
    ),

    avaliacao: (
      <>
        <Rect x="5" y="4" width="14" height="18" rx="2" />
        <Rect x="9" y="2" width="6" height="4" rx="1" />
        <Path d="M12 10v7M8.5 13.5h7" />
      </>
    ),

    perfil: (
      <>
        <Circle cx="12" cy="8" r="4" />
        <Path d="M4 22v-2a8 8 0 0 1 16 0v2" />
      </>
    ),

    ajuda: (
      <>
        <Circle cx="12" cy="12" r="9" />
        <Path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4" />
        <Circle cx="12" cy="17" r=".5" fill={cor} />
      </>
    ),

    livro: (
      <>
        <Path d="M12 5C9 2 5 3 2 4v16c4-2 7-2 10 0" />
        <Path d="M12 5c3-3 7-2 10-1v16c-4-2-7-2-10 0Z" />
      </>
    ),

    olho: (
      <>
        <Path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
        <Circle cx="12" cy="12" r="3" />
      </>
    ),

    'olho-fechado': (
      <>
        <Path d="m3 3 18 18" />
        <Path d="M10 6a11 11 0 0 1 2 0c6.5 0 10 6 10 6a16 16 0 0 1-3 3" />
        <Path d="M6 6C3 8 2 12 2 12s3.5 6 10 6a10 10 0 0 0 4-1" />
      </>
    ),

    email: (
      <>
        <Rect x="2" y="4" width="20" height="16" rx="2" />
        <Path d="m2 6 10 7L22 6" />
      </>
    ),

    cadeado: (
      <>
        <Rect x="4" y="10" width="16" height="12" rx="2" />
        <Path d="M8 10V6a4 4 0 0 1 8 0v4" />
        <Path d="M12 15v3" />
      </>
    ),

    seta: <Path d="m9 5 7 7-7 7" />,

    escudo: (
      <>
        <Path d="m12 2 8 4v6c0 5-4 8-8 10-4-2-8-5-8-10V6Z" />
        <Path d="m8 12 3 3 5-6" />
      </>
    ),

    camera: (
      <>
        <Path d="M3 6h5l2-3h4l2 3h5v15H3Z" />
        <Circle cx="12" cy="13" r="4" />
      </>
    ),

    imagem: (
      <>
        <Rect x="3" y="3" width="18" height="18" rx="2" />
        <Circle cx="8" cy="8" r="2" />
        <Path d="m3 18 6-6 4 4 3-3 5 5" />
      </>
    ),

    editar: (
      <>
        <Path d="m14 5 5 5" />
        <Path d="m4 15 12-12 5 5L9 20l-6 1Z" />
      </>
    ),

    pesquisa: (
      <>
        <Circle cx="10.5" cy="10.5" r="6.5" />
        <Path d="m16 16 5 5" />
      </>
    ),

    arquivo: (
      <>
        <Path d="M5 2h9l5 5v15H5Z" />
        <Path d="M14 2v6h5M8 12h8M8 16h8" />
      </>
    ),

    sair: (
      <>
        <Path d="M10 3H3v18h7M8 12h13m-5-5 5 5-5 5" />
      </>
    ),

    confirmar: <Path d="m5 12 4 4L19 6" />,
  };

  return (
    <Svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke={cor}
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {desenhos[nome]}
    </Svg>
  );
}
