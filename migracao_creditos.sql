-- VarVid — colunas novas na tabela profiles
--
-- Onde rodar: Supabase → SQL Editor → New query → colar → Run.
-- Leva um segundo e não apaga nada.
--
-- POR QUE PRECISA:
-- A reposição de créditos deixou de depender do Stripe avisar que uma fatura foi
-- paga. Aquele modelo quebrava de duas formas: o aviso só chega com o webhook
-- configurado (não estava, então ninguém era reposto depois do primeiro mês), e
-- no plano anual ele chega uma vez por ano — quem pagasse doze meses receberia
-- a cota de um.
--
-- Agora cada perfil carrega a própria data de renovação. Estas duas colunas são
-- onde ela mora. Sem elas, o app continua funcionando, mas nenhuma reposição é
-- gravada.

alter table profiles add column if not exists ciclo text;
alter table profiles add column if not exists renova_em timestamptz;

-- Quem já é assinante hoje (se houver) fica sem data e nunca seria reposto.
-- Esta linha marca a próxima renovação para daqui a um mês, tratando todo mundo
-- como mensal. Se algum desses já tiver assinado no anual, ajuste na mão depois.
update profiles
   set ciclo = coalesce(ciclo, 'mensal'),
       renova_em = coalesce(renova_em, now() + interval '1 month')
 where plan is not null
   and plan <> 'free';

-- Conferência: deve listar os assinantes com a data preenchida.
select id, plan, ciclo, credits, renova_em
  from profiles
 where plan is not null and plan <> 'free';
