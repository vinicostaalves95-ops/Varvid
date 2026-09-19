-- VarVid — conceder o plano UMA vez por pagamento
-- Rode no SQL Editor do Supabase. Pode rodar mais de uma vez sem estragar nada.

-- Cada pagamento aprovado no Stripe é uma "checkout session" com id único.
-- Guardar esse id aqui é o que permite duas coisas:
--
--   1. a página de retorno (/billing/success) e o webhook do Stripe podem
--      chamar o mesmo código sem risco: quem chegar primeiro concede o plano,
--      o segundo vê que já foi e não faz nada;
--
--   2. recarregar a URL de retorno deixa de dar crédito de novo. Antes dava:
--      set_plan() SOMA créditos, então quem guardasse aquele endereço ganhava
--      a cota a cada F5.
--
-- A chave primária é o próprio id da sessão. Isso torna a marcação ATÔMICA: o
-- banco recusa o segundo INSERT, e é essa recusa — não uma consulta antes — que
-- decide quem concede. Consultar-depois-gravar teria uma fresta entre os dois
-- passos, e é exatamente nessa fresta que a cobrança em dobro mora.
create table if not exists checkouts_processados (
  session_id  text primary key,
  uid         text,
  plano       text,
  ciclo       text,
  criado_em   timestamptz default now()
);

-- Só o servidor (service key) escreve aqui; nenhum usuário precisa enxergar.
alter table checkouts_processados enable row level security;
