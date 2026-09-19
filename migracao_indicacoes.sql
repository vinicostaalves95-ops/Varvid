-- VarVid — member get member
-- Rode no SQL Editor do Supabase. Pode rodar mais de uma vez sem estragar nada.

-- O código que a pessoa compartilha. É derivado do id dela, então é sempre o
-- mesmo — não precisa sortear nem conferir colisão na hora de criar.
alter table profiles add column if not exists referral_code text;

-- Quem trouxe esta pessoa. Gravado UMA vez, no primeiro acesso, e nunca mais
-- mexido: se pudesse mudar depois, qualquer um se atribuiria a indicação.
alter table profiles add column if not exists referred_by text;

-- As duas marcas de pagamento vivem na linha de QUEM FOI INDICADO, não na de
-- quem indicou. É de propósito: cada indicado só pode gerar cada bônus uma vez,
-- e a marca fica colada no evento que ela representa. Guardar só um contador no
-- indicador deixaria a conta certa e a origem invisível — e foi exatamente esse
-- tipo de selo no lugar errado que causou o bug de cobrança de 19/09.
alter table profiles add column if not exists ref_ativou boolean default false;
alter table profiles add column if not exists ref_pagou  boolean default false;

-- Busca por código acontece em todo cadastro com link de indicação.
create unique index if not exists profiles_referral_code_idx
  on profiles (referral_code) where referral_code is not null;

create index if not exists profiles_referred_by_idx
  on profiles (referred_by) where referred_by is not null;
